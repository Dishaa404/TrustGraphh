import { expect } from "chai";
import { ethers } from "hardhat";
import { loadFixture, time } from "@nomicfoundation/hardhat-network-helpers";

const did = (label: string) => ethers.keccak256(ethers.toUtf8Bytes(`did:trustgraph:${label}`));
const schema = (label: string) => ethers.keccak256(ethers.toUtf8Bytes(`schema:${label}`));
const content = (label: string) => ethers.keccak256(ethers.toUtf8Bytes(`content:${label}`));

async function deployFixture() {
  const [owner, issuer, other] = await ethers.getSigners();

  const registry = await ethers.deployContract("CredentialRegistry", [owner.address]);
  await registry.waitForDeployment();
  await registry.setIssuer(issuer.address, true);

  return { registry, owner, issuer, other };
}

describe("CredentialRegistry", () => {
  it("issues a credential anchored by hash and CID", async () => {
    const { registry, issuer } = await loadFixture(deployFixture);
    const expiry = (await time.latest()) + 86400;

    await expect(
      registry
        .connect(issuer)
        .issue(did("alice"), schema("kyc"), content("kyc-1"), expiry, "ipfs://bafy-kyc"),
    ).to.emit(registry, "Issued");

    const [credentialId] = await registry.getSubjectCredentials(did("alice"));
    const credential = await registry.getCredential(credentialId);

    expect(credential.subjectDid).to.equal(did("alice"));
    expect(credential.issuer).to.equal(issuer.address);
    expect(credential.cid).to.equal("ipfs://bafy-kyc");
    expect(await registry.isValid(credentialId)).to.equal(true);
  });

  it("rejects issuance from non-issuers and invalid inputs", async () => {
    const { registry, issuer, other } = await loadFixture(deployFixture);
    const expiry = (await time.latest()) + 86400;

    await expect(
      registry
        .connect(other)
        .issue(did("alice"), schema("kyc"), content("kyc-1"), expiry, "ipfs://x"),
    ).to.be.revertedWithCustomError(registry, "NotIssuer");

    await expect(
      registry.connect(issuer).issue(ethers.ZeroHash, schema("kyc"), content("x"), 0, ""),
    ).to.be.revertedWithCustomError(registry, "InvalidSubject");
  });

  it("rejects expired issuance timestamps", async () => {
    const { registry, issuer } = await loadFixture(deployFixture);
    const past = (await time.latest()) - 1;

    await expect(
      registry
        .connect(issuer)
        .issue(did("alice"), schema("kyc"), content("kyc-1"), past, "ipfs://x"),
    ).to.be.revertedWithCustomError(registry, "InvalidExpiry");
  });

  it("revokes credentials and reports them invalid", async () => {
    const { registry, issuer, other } = await loadFixture(deployFixture);
    const expiry = (await time.latest()) + 86400;

    await registry
      .connect(issuer)
      .issue(did("alice"), schema("kyc"), content("kyc-1"), expiry, "ipfs://bafy-kyc");

    const [credentialId] = await registry.getSubjectCredentials(did("alice"));

    await expect(registry.connect(other).revoke(credentialId, "nope")).to.be.revertedWithCustomError(
      registry,
      "NotIssuer",
    );

    await expect(registry.connect(issuer).revoke(credentialId, "lost job"))
      .to.emit(registry, "Revoked")
      .withArgs(credentialId, issuer.address, "lost job");

    expect(await registry.isValid(credentialId)).to.equal(false);
    expect((await registry.getCredential(credentialId)).revoked).to.equal(true);
  });

  it("treats unknown and expired credentials as invalid", async () => {
    const { registry, issuer } = await loadFixture(deployFixture);
    const expiry = (await time.latest()) + 86400;

    expect(await registry.isValid(ethers.ZeroHash)).to.equal(false);

    await registry
      .connect(issuer)
      .issue(did("alice"), schema("kyc"), content("kyc-1"), expiry, "ipfs://x");

    const [credentialId] = await registry.getSubjectCredentials(did("alice"));
    expect(await registry.isValid(credentialId)).to.equal(true);

    await time.increaseTo(expiry + 1);
    expect(await registry.isValid(credentialId)).to.equal(false);
  });
});
