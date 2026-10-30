import "dotenv/config";
import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";

const privateKey = process.env.PRIVATE_KEY ?? "";
const normalizedPrivateKey = privateKey.startsWith("0x") ? privateKey : `0x${privateKey}`;
const accounts = /^0x[0-9a-fA-F]{64}$/.test(normalizedPrivateKey)
  ? [normalizedPrivateKey]
  : [];
if (privateKey && accounts.length === 0) {
  throw new Error("PRIVATE_KEY must be a 32-byte hex key, with or without a 0x prefix.");
}

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: { enabled: true, runs: 200 },
    },
  },
  networks: {
    hardhat: {
      chainId: 31337,
    },
    baseSepolia: {
      url: process.env.BASE_SEPOLIA_RPC_URL ?? "https://sepolia.base.org",
      chainId: 84532,
      accounts,
    },
  },
  etherscan: {
    apiKey: {
      baseSepolia: process.env.BASE_SEPOLIA_ETHERSCAN_API_KEY ?? "",
    },
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
};

export default config;
