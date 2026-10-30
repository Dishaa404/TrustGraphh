import { expect } from "chai";
import { ethers } from "hardhat";
import { loadFixture } from "@nomicfoundation/hardhat-network-helpers";

const STATUS = { None: 0n, Pending: 1n, Active: 2n, Challenged: 3n, Revoked: 4n };

const did = (label: string) => ethers.keccak256(ethers.toUtf8Bytes(`did:trustgraph:${label}`));
const bio = (label: string) => ethers.keccak256(ethers.toUtf8Bytes(`bio:${label}`));

async function deployFixture() {
  const [owner, treasury, alice, bob, carol, dave, eve, challenger, outsider] =
    await ethers.getSigners();

  const registry = await ethers.deployContract("PersonhoodRegistry", [
    owner.address,
    treasury.address,
  ]);
  await registry.waitForDeployment();

  return { registry, owner, treasury, alice, bob, carol, dave, eve, challenger, outsider };
}

async function activeHumansFixture() {
  const base = await deployFixture();
  const { registry, alice, bob, carol, dave } = base;

  await registry.setConfig(ethers.parseEther("0.001"), ethers.parseEther("0.002"), 0, 3 * 86400);
  for (const [signer, label] of [
    [alice, "alice"],
    [bob, "bob"],
    [carol, "carol"],
    [dave, "dave"],
  ] as const) {
    await registry.connect(signer).register(did(label), bio(label), {
      value: ethers.parseEther("0.001"),
    });
  }

  return base;
}

describe("PersonhoodRegistry", () => {
  describe("registration", () => {
    it("registers a pending human and maps the wallet", async () => {
      const { registry, alice } = await loadFixture(deployFixture);

      await expect(
        registry.connect(alice).register(did("alice"), bio("alice"), {
          value: ethers.parseEther("0.001"),
        }),
      )
        .to.emit(registry, "Registered")
        .withArgs(did("alice"), alice.address, ethers.parseEther("0.001"));

      const human = await registry.getHuman(did("alice"));
      expect(human.wallet).to.equal(alice.address);
      expect(human.status).to.equal(STATUS.Pending);
      expect(await registry.walletToDid(alice.address)).to.equal(did("alice"));
      expect(await registry.humanCount()).to.equal(1n);
      expect(await registry.isHuman(alice.address)).to.equal(false);
    });

    it("rejects duplicate DIDs and reused wallets", async () => {
      const { registry, alice, bob } = await loadFixture(deployFixture);
      const stake = { value: ethers.parseEther("0.001") };

      await registry.connect(alice).register(did("alice"), bio("alice"), stake);

      await expect(
        registry.connect(bob).register(did("alice"), bio("bob"), stake),
      ).to.be.revertedWithCustomError(registry, "AlreadyRegistered");

      await expect(
        registry.connect(alice).register(did("alice2"), bio("alice2"), stake),
      ).to.be.revertedWithCustomError(registry, "WalletInUse");
    });

    it("requires the exact stake and blocks zero DIDs", async () => {
      const { registry, alice } = await loadFixture(deployFixture);

      await expect(
        registry.connect(alice).register(did("alice"), bio("alice"), { value: 1n }),
      ).to.be.revertedWithCustomError(registry, "InvalidStake");

      await expect(
        registry.connect(alice).register(ethers.ZeroHash, bio("alice"), {
          value: ethers.parseEther("0.001"),
        }),
      ).to.be.revertedWithCustomError(registry, "InvalidDid");
    });

    it("auto-activates when no vouches are required", async () => {
      const { registry, alice } = await loadFixture(deployFixture);
      await registry.setConfig(0, 0, 0, 0);

      await registry.connect(alice).register(did("alice"), bio("alice"));

      expect(await registry.isHuman(alice.address)).to.equal(true);
    });

    it("can be paused by the owner", async () => {
      const { registry, alice } = await loadFixture(deployFixture);
      await registry.pause();

      await expect(
        registry.connect(alice).register(did("alice"), bio("alice"), {
          value: ethers.parseEther("0.001"),
        }),
      ).to.be.revertedWithCustomError(registry, "EnforcedPause");
    });
  });

  describe("vouching", () => {
    it("activates a human once the vouch threshold is met", async () => {
      const { registry, alice, bob, dave, eve } = await loadFixture(activeHumansFixture);
      await registry.setConfig(ethers.parseEther("0.001"), ethers.parseEther("0.002"), 2, 0);
      await registry.connect(eve).register(did("eve"), bio("eve"), {
        value: ethers.parseEther("0.001"),
      });

      await expect(registry.connect(alice).vouch(did("eve")))
        .to.emit(registry, "Vouched")
        .withArgs(did("eve"), did("alice"), 1);

      expect((await registry.getHuman(did("eve"))).status).to.equal(STATUS.Pending);

      await expect(registry.connect(bob).vouch(did("eve")))
        .to.emit(registry, "Activated")
        .withArgs(did("eve"), eve.address, (v: bigint) => v > 0n);

      expect(await registry.isHuman(eve.address)).to.equal(true);
      expect(await registry.getVouchers(did("eve"))).to.deep.equal([did("alice"), did("bob")]);
      expect(dave.address).to.be.properAddress;
    });

    it("rejects vouches from unregistered or pending accounts", async () => {
      const { registry, alice, eve, outsider } = await loadFixture(activeHumansFixture);
      await registry.setConfig(ethers.parseEther("0.001"), ethers.parseEther("0.002"), 3, 0);
      await registry.connect(eve).register(did("eve"), bio("eve"), {
        value: ethers.parseEther("0.001"),
      });

      await expect(
        registry.connect(outsider).vouch(did("eve")),
      ).to.be.revertedWithCustomError(registry, "NotRegistered");

      await expect(
        registry.connect(eve).vouch(did("alice")),
      ).to.be.revertedWithCustomError(registry, "VoucherNotActive");

      await expect(
        registry.connect(alice).vouch(did("alice")),
      ).to.be.revertedWithCustomError(registry, "InvalidStatus");
    });

    it("prevents duplicate vouches before activation", async () => {
      const { registry, alice, eve } = await loadFixture(activeHumansFixture);
      await registry.setConfig(ethers.parseEther("0.001"), ethers.parseEther("0.002"), 3, 0);
      await registry.connect(eve).register(did("eve"), bio("eve"), {
        value: ethers.parseEther("0.001"),
      });

      await registry.connect(alice).vouch(did("eve"));

      await expect(
        registry.connect(alice).vouch(did("eve")),
      ).to.be.revertedWithCustomError(registry, "AlreadyVouched");
    });
  });

  describe("challenges", () => {
    it("revokes an upheld challenge and pays the challenger", async () => {
      const { registry, treasury, dave, challenger } = await loadFixture(activeHumansFixture);
      const challengeStake = ethers.parseEther("0.002");
      const registrationStake = ethers.parseEther("0.001");

      await registry.connect(challenger).challenge(did("dave"), { value: challengeStake });
      expect((await registry.getHuman(did("dave"))).status).to.equal(STATUS.Challenged);

      await expect(registry.connect(treasury).resolveChallenge(did("dave"), true)).to.be.revertedWithCustomError(
        registry,
        "NotArbitrator",
      );

      await expect(registry.resolveChallenge(did("dave"), true)).to.emit(registry, "ChallengeResolved");

      expect((await registry.getHuman(did("dave"))).status).to.equal(STATUS.Revoked);
      expect(await registry.pendingWithdrawal(challenger.address)).to.equal(
        challengeStake + registrationStake / 2n,
      );
      expect(await registry.pendingWithdrawal(treasury.address)).to.equal(
        registrationStake - registrationStake / 2n,
      );
    });

    it("keeps the human active when a challenge is rejected", async () => {
      const { registry, treasury, dave, challenger } = await loadFixture(activeHumansFixture);
      const challengeStake = ethers.parseEther("0.002");

      await registry.connect(challenger).challenge(did("dave"), { value: challengeStake });
      await registry.resolveChallenge(did("dave"), false);

      expect((await registry.getHuman(did("dave"))).status).to.equal(STATUS.Active);
      expect(await registry.pendingWithdrawal(treasury.address)).to.equal(challengeStake);
      expect(await registry.isHuman(dave.address)).to.equal(true);
    });

    it("only allows active humans to be challenged and requires the stake", async () => {
      const { registry, eve, challenger, alice } = await loadFixture(activeHumansFixture);
      const challengeStake = ethers.parseEther("0.002");

      await expect(
        registry.connect(challenger).challenge(did("eve"), { value: challengeStake }),
      ).to.be.revertedWithCustomError(registry, "InvalidStatus");

      await expect(
        registry.connect(challenger).challenge(did("alice"), { value: 1n }),
      ).to.be.revertedWithCustomError(registry, "InvalidStake");

      await expect(
        registry.connect(alice).challenge(did("alice"), { value: challengeStake }),
      ).to.be.revertedWithCustomError(registry, "SelfVouch");
    });

    it("supports emergency revocation and withdrawal", async () => {
      const { registry, treasury, dave } = await loadFixture(activeHumansFixture);

      await expect(registry.revoke(did("dave"), "fraud ring"))
        .to.emit(registry, "Revoked")
        .withArgs(did("dave"), "fraud ring");

      expect((await registry.getHuman(did("dave"))).status).to.equal(STATUS.Revoked);
      expect(await registry.pendingWithdrawal(treasury.address)).to.equal(
        ethers.parseEther("0.001"),
      );

      await expect(registry.connect(treasury).withdraw()).to.changeEtherBalances(
        [treasury],
        [ethers.parseEther("0.001")],
      );
    });
  });
});
