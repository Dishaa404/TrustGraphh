import { ethers } from "hardhat";

async function main() {
  const network = await ethers.provider.getNetwork();
  if (network.chainId !== 84532n) {
    throw new Error(`Refusing deployment on chain ${network.chainId}; expected Base Sepolia (84532).`);
  }
  if (!process.env.PRIVATE_KEY) {
    throw new Error("PRIVATE_KEY is required. Copy contracts/.env.example to contracts/.env and configure a funded testnet deployer.");
  }

  const [deployer] = await ethers.getSigners();
  const treasury = process.env.TREASURY_ADDRESS ?? deployer.address;
  if (!ethers.isAddress(treasury)) {
    throw new Error("TREASURY_ADDRESS must be a valid EVM address.");
  }

  console.log("Deploying with", deployer.address);
  console.log("Treasury:", treasury);

  const personhood = await ethers.deployContract("PersonhoodRegistry", [
    deployer.address,
    treasury,
  ]);
  await personhood.waitForDeployment();

  const credentials = await ethers.deployContract("CredentialRegistry", [deployer.address]);
  await credentials.waitForDeployment();

  console.log(
    JSON.stringify(
      {
        network: "baseSepolia",
        chainId: Number(network.chainId),
        deployer: deployer.address,
        treasury,
        personhoodRegistry: await personhood.getAddress(),
        credentialRegistry: await credentials.getAddress(),
      },
      null,
      2,
    ),
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
