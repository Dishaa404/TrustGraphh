import { ethers } from "hardhat";

async function main() {
  const [deployer] = await ethers.getSigners();
  const treasury = process.env.TREASURY_ADDRESS ?? deployer.address;

  console.log("Deploying with", deployer.address);
  console.log("Treasury:", treasury);

  const personhood = await ethers.deployContract("PersonhoodRegistry", [
    deployer.address,
    treasury,
  ]);
  await personhood.waitForDeployment();

  const credentials = await ethers.deployContract("CredentialRegistry", [deployer.address]);
  await credentials.waitForDeployment();

  console.log("PersonhoodRegistry:", await personhood.getAddress());
  console.log("CredentialRegistry:", await credentials.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
