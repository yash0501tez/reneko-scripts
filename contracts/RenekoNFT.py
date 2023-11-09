import smartpy as sp

FA2 = sp.io.import_script_from_url("https://legacy.smartpy.io/templates/fa2_lib.py")
Utils = sp.io.import_script_from_url("https://raw.githubusercontent.com/RomarQ/tezos-sc-utils/main/smartpy/utils.py")

class NFT(
    FA2.Admin,
    FA2.BurnNft,
    FA2.MintNft,
    FA2.ChangeMetadata,
    FA2.OnchainviewBalanceOf,
    FA2.OffchainviewTokenMetadata,
    FA2.WithdrawMutez,
    FA2.Fa2Nft
):
    def __init__(self, admin ,**kwargs):
        FA2.Fa2Nft.__init__(self, policy=FA2.NoTransfer(), **kwargs)
        FA2.Admin.__init__(self, admin)

    @sp.entry_point
    def updateTokenMetadata(self, params):
        sp.set_type(params, sp.TMap(sp.TNat, sp.TBytes))
        sp.verify(sp.sender == self.data.administrator, 'FA2_NOT_ADMIN')
        sp.for tokenId in params.keys():
            self.data.token_metadata[tokenId] = sp.record(
                token_id=tokenId, 
                token_info=sp.map({'': params[tokenId]})
            )

    # @sp.onchain_view()
    # def getTotalSupply(self):
    #     sp.result(self.data.last_token_id)

    # @sp.entry_point
    # def updateBaseURI(self, _uri):
    #     sp.verify(sp.sender == self.data.administrator, 'FA2_NOT_ADMIN')
    #     self.data.baseURI = _uri

class RenekoProxy(sp.Contract):    
    def __init__(self):
        self.init_type(sp.TRecord(
            admin = sp.TAddress,
            userNonce = sp.TBigMap(sp.TAddress, sp.TNat),
            TrustedForwarder = sp.TAddress,
            adjustableCost = sp.TMutez,
            nftContract = sp.TAddress,
        ))

    def verifyUser(self, params):
        # sp.trace(sp.sender)
        sp.verify(sp.sender == self.data.TrustedForwarder, "Sender is not Trusted Forwarder")
        # record = params.open_some()
        record = params
        sp.trace(record)
        sp.verify(sp.check_signature(record.key, record.sig, record.data_bytes), "Signature is not valid")
        sender = sp.to_address(sp.implicit_account(sp.hash_key(record.key)))
        sp.trace(sender)
        return sender
    
    def mint(self, batch):
        sp.set_type(
            batch,
            sp.TList(
                sp.TRecord(
                    to_=sp.TAddress,
                    metadata=sp.TMap(sp.TString, sp.TBytes),
                ).layout(("to_", "metadata"))
            ),
        )
        mint_arg_type = sp.TList(
            sp.TRecord(
                to_=sp.TAddress,
                metadata=sp.TMap(sp.TString, sp.TBytes),
            ).layout(("to_", "metadata"))
        )
        c = sp.contract(mint_arg_type, self.data.nftContract, "mint").open_some()
        sp.transfer(batch, sp.tez(0), c)
    
    @sp.entry_point
    def adminMint(self, params):
        # verify sender is admin
        sp.verify(sp.sender == self.data.admin, 'NOT_ADMIN')
        # map(to, metadata_bytes)
        sp.set_type(params, sp.TMap(sp.TAddress, sp.TBytes))
        # loop through map
        mint_list = sp.local('mint_list', sp.list())
        sp.for _to in params.keys():
            sp.trace(_to)
            sp.trace(params[_to])
            # mint to user
            mint_list.value.push(sp.record(
                to_=_to, 
                metadata = {
                    '': params[_to]
                }
            ))
        self.mint(mint_list.value)

    @sp.entry_point
    def generalMint(self, params):
        # verify signature
        sender = sp.local('sender', self.verifyUser(params._meta))
        # sender = self.verifyUser(params._meta)
        record_type = sp.TRecord(
            _ipfsHash = sp.TBytes,
            _nonce = sp.TNat,
            _ttl = sp.TNat,
        ).layout(("_ipfsHash", ("_nonce", "_ttl")))
        # data = sp.unpack(params._meta.open_some().data_bytes, record_type).open_some()
        data = sp.unpack(params._meta.data_bytes, record_type).open_some()
        sp.trace(data)
        sp.verify(params._ipfsHash == data._ipfsHash, "IPFS hash is not valid")

        # verify nonce
        sp.if self.data.userNonce.contains(sender.value):
            sp.verify(self.data.userNonce[sender.value] < data._nonce, "Transaction not valid")
        sp.trace(data)
        sp.verify(data._ttl > sp.utils.seconds_of_timestamp(sp.now), "Signature already expired")

        self.data.userNonce[sender.value] = data._nonce

        # mint to user
        self.mint(sp.list([
            sp.record(
                to_=sender.value, 
                metadata = {
                    '': params._ipfsHash
                }
            )
        ]))

    @sp.entry_point
    def updateTokenMetadata(self, params):
        sp.verify(sp.sender == self.data.admin, 'NOT_ADMIN')
        sp.set_type(params, sp.TMap(sp.TNat, sp.TBytes))

        params_type = sp.TMap(sp.TNat, sp.TBytes)
        c = sp.contract(params_type, self.data.nftContract, "updateTokenMetadata").open_some()
        sp.transfer(params, sp.tez(0), c)

    @sp.entry_point
    def setAdmin(self, admin):
        sp.verify(sp.sender == self.data.admin, 'NOT_ADMIN')
        self.data.admin = admin

    @sp.entry_point
    def setTrustedForwarder(self, forwarder):
        sp.verify(sp.sender == self.data.admin, 'NOT_ADMIN')
        self.data.TrustedForwarder = forwarder

    @sp.entry_point
    def setNftContract(self, contract):
        sp.verify(sp.sender == self.data.admin, 'NOT_ADMIN')
        self.data.nftContract = contract

    @sp.entry_point
    def setAdjustableCost(self, cost):
        sp.verify(sp.sender == self.data.admin, 'NOT_ADMIN')
        self.data.adjustableCost = cost

    @sp.entry_point
    def burn(self, params):
        sp.verify(self.data.admin == sp.sender, 'GPK_NOT_ADMIN')
        params_type = sp.TList(sp.TRecord(amount = sp.TNat, from_ = sp.TAddress, token_id = sp.TNat).layout(("from_", ("token_id", "amount"))))
        c = sp.contract(params_type, self.data.nftContract, "burn").open_some()
        sp.transfer(params, sp.tez(0), c)

    @sp.entry_point
    def setNftContractAdministrator(self, params):
        sp.verify(self.data.admin == sp.sender, 'GPK_NOT_ADMIN')
        params_type = sp.TAddress
        c = sp.contract(params_type, self.data.nftContract, "set_administrator").open_some()
        sp.transfer(params, sp.tez(0), c)

    @sp.entry_point
    def set_metadata(self, params):
        sp.verify(self.data.admin == sp.sender, 'GPK_NOT_ADMIN')
        params_type = sp.TBigMap(sp.TString, sp.TBytes)
        c = sp.contract(params_type, self.data.nftContract, "set_metadata").open_some()
        sp.transfer(params, sp.tez(0), c)

    @sp.entry_point
    def transfer(self, params):
        sp.verify(self.data.admin == sp.sender, 'GPK_NOT_ADMIN')
        params_type = sp.TList(sp.TRecord(from_ = sp.TAddress, txs = sp.TList(sp.TRecord(amount = sp.TNat, to_ = sp.TAddress, token_id = sp.TNat).layout(("to_", ("token_id", "amount"))))).layout(("from_", "txs")))
        c = sp.contract(params_type, self.data.nftContract, "transfer").open_some()
        sp.transfer(params, sp.tez(0), c)

    @sp.entry_point
    def update_operators(self, params):
        sp.verify(self.data.admin == sp.sender, 'GPK_NOT_ADMIN')
        params_type = sp.TList(sp.TVariant(add_operator = sp.TRecord(operator = sp.TAddress, owner = sp.TAddress, token_id = sp.TNat).layout(("owner", ("operator", "token_id"))), remove_operator = sp.TRecord(operator = sp.TAddress, owner = sp.TAddress, token_id = sp.TNat).layout(("owner", ("operator", "token_id")))).layout(("add_operator", "remove_operator")))
        c = sp.contract(params_type, self.data.nftContract, "update_operators").open_some()
        sp.transfer(params, sp.tez(0), c)

@sp.add_test(name = "Reneko NFT")
def test():
    scenario = sp.test_scenario()
    scenario.h1("Reneko NFT")
    # admin = sp.test_account("admin")
    user = sp.test_account("user")
    # trustedForwarder = sp.test_account("trustedForwarder")
    admin = sp.address("tz1Rqm76xELsDa7fpjeX8gfAt4imV2fVMmhn")
    trustedForwarder = sp.address("tz1iWU9xwe1gbboxefyWadcmFeg2yMMLQ8Ap")
    
    # Deploy NFT contract
    token_contract = NFT(admin = admin, metadata = sp.utils.metadata_of_url("https://bafkreie5l4x4jxygeslvvvhzjjecvcooyvn7qg7l6snbkpur7jvmqij2ie.ipfs.dweb.link/"))
    scenario += token_contract

    # Deploy RenekoProxy contract
    proxy_contract = RenekoProxy()
    proxy_contract.init_storage(
        sp.record(
            admin = admin,
            userNonce = sp.big_map({}),
            TrustedForwarder = trustedForwarder,
            adjustableCost = sp.tez(0),
            nftContract = token_contract.address,
        )
    )
    scenario += proxy_contract

    scenario += token_contract.set_administrator(proxy_contract.address).run(sender=admin)

    # Mint NFT Admin
    scenario.h2("Mint NFT Admin")
    scenario += proxy_contract.adminMint(sp.map({
        user.address: sp.bytes('0x0505050505050505050505050505050505050505050505050505050505050505')
    })).run(sender = admin)

    generalMintParams = sp.record(
        _ipfsHash = sp.bytes("0x697066733a2f"),
        _meta = sp.record(
            key=sp.key("edpkvZNHsSBU9XXHin49qMiv1kwrfdFLuNY3Sm7H6F5e4L7GCbbH7K"), 
            sig=sp.signature("edsigtXqygSPzVdd7GtC8guvRk93K5Y7yNtCWNguanQeFmP7owhubnWAic1uxzdoFyoNwHeEDx684SPeB4Fm8M1MYiFH67eC92N"), 
            data_bytes=sp.bytes("0x050707010000000c363937303636373333613266070700a40100a401")
        )
    )
    scenario += proxy_contract.generalMint(generalMintParams).run(sender=trustedForwarder, now=sp.timestamp(99))

    # change token metadata
    scenario.h2("Update Token Metadata")
    scenario += proxy_contract.updateTokenMetadata(sp.map({
        1: sp.bytes('0x0505050505050505050505050505050505050505050505050505050505050505')
    })).run(sender=admin)
