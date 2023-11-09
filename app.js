const express = require("express");
const app = express();
const cors = require("cors");
const { InMemorySigner } = require("@taquito/signer");
const { TezosToolkit, MichelsonMap } = require("@taquito/taquito");
const dotenv = require("dotenv");
dotenv.config();

const Tezos = new TezosToolkit("https://ghostnet.smartpy.io/");
InMemorySigner.fromSecretKey(process.env.PVT_KEY)
  .then((signer) => {
    Tezos.setProvider({
      signer: signer,
    });
    return Tezos.signer.publicKeyHash();
  })
  .then((pkh) => console.log(`Initialized account ${pkh}`))
  .catch((error) => console.log(`Error: ${error} `));

app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
  res.send("Hello World!");
});

app.post("/doGeneralMint", async (req, res) => {
  const { address, bytes, amount } = req.body;
  const transactionMap = new MichelsonMap();
  transactionMap.set(address, bytes);
  try {
    (await Tezos.contract.at(process.env.CONTRACT_ADDRESS)).methods
      .adminMint(transactionMap)
      .send()
      .then((op) => {
        console.log(op);
        res.send(op.confirmation(2));
      })
      .catch((err) => {
        console.log(err);
        res.send(err);
      });
  } catch (err) {
    res.send(err);
  }
});

app.listen(3000, () => {
  console.log("Server is running on port 3000");
});
