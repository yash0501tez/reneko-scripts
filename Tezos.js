const express = require("express");
const app = express();
const cors = require("cors");
const { InMemorySigner } = require("@taquito/signer");
const { TezosToolkit } = require("@taquito/taquito");
const { char2Bytes } = require("@taquito/utils");
const { Parser, packDataBytes } = require("@taquito/michel-codec");
const dotenv = require("dotenv");
dotenv.config();

const Tezos = new TezosToolkit("https://ghostnet.smartpy.io/");
const signer = InMemorySigner.fromSecretKey(process.env.PVT_KEY);

Tezos.setProvider({ signer });

app.use(cors());
app.use(express.json());

const makeSignature = async (data, type) => {
    let p = new Parser();
  
    const dataJSON = p.parseMichelineExpression(data);
    const typeJSON = p.parseMichelineExpression(type);
  
    const packed = packDataBytes(dataJSON, typeJSON);
  
    const signed = await (await signer).sign(packed.bytes, new Uint8Array([3]));
    console.log(signed);
  
    let result = {
      bytes: packed.bytes,
      sig: signed.signature,
    };
    console.log(result);
    return signed;
  };

  const generalMint = async (_ipfsUrl, nonce, ttl) => {
    let _ipfsHash = char2Bytes(_ipfsUrl);
    console.log(_ipfsHash);
    let data = `(Pair "${_ipfsHash}" (Pair ${nonce} ${ttl}))`;
    let type = `(pair (bytes) (pair (nat) (nat)))`;
  
    let result = await makeSignature(data, type);
    console.log(result, _ipfsHash);
    return {result, _ipfsHash};
  };

app.post("/makeSignature", async (req, res) => {
  const { _ipfsUrl, nonce, ttl } = req.body;
  res.send(await generalMint(_ipfsUrl, nonce, ttl))
});

app.listen(5000, () => {
  console.log("Example app listening on port 5000!");
});
