// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title PersonhoodRegistry
/// @notice Stake-backed human registry with social vouching, challenges, and revocation.
/// @dev Trust scoring lives off-chain in TigerGraph. This contract is the source of truth
///      for membership status and staked collateral.
contract PersonhoodRegistry is Ownable, Pausable, ReentrancyGuard {
    enum Status {
        None,
        Pending,
        Active,
        Challenged,
        Revoked
    }

    struct Human {
        address wallet;
        bytes32 biometricHash;
        uint64 registeredAt;
        uint64 activeAt;
        uint64 challengeEndsAt;
        uint32 vouchCount;
        uint256 stake;
        uint256 challengeDeposit;
        Status status;
        address challenger;
    }

    uint256 public registrationStake = 0.001 ether;
    uint256 public challengeStake = 0.002 ether;
    uint32 public requiredVouches = 3;
    uint64 public challengeWindow = 3 days;
    address public treasury;
    uint256 public totalStaked;

    mapping(bytes32 => Human) private _humans;
    mapping(address => bytes32) public walletToDid;
    mapping(bytes32 => bytes32[]) private _vouchers;
    mapping(bytes32 => mapping(bytes32 => bool)) public hasVouched;
    mapping(address => bool) public isArbitrator;
    mapping(address => uint256) public pendingWithdrawal;
    bytes32[] private _dids;

    event Registered(bytes32 indexed didHash, address indexed wallet, uint256 stake);
    event Vouched(bytes32 indexed didHash, bytes32 indexed voucherDid, uint32 vouchCount);
    event Activated(bytes32 indexed didHash, address indexed wallet, uint64 activeAt);
    event Challenged(
        bytes32 indexed didHash,
        address indexed challenger,
        uint256 stake,
        uint64 challengeEndsAt
    );
    event ChallengeResolved(bytes32 indexed didHash, bool upheld, address indexed challenger);
    event Revoked(bytes32 indexed didHash, string reason);
    event ConfigUpdated(
        uint256 registrationStake,
        uint256 challengeStake,
        uint32 requiredVouches,
        uint64 challengeWindow
    );
    event ArbitratorUpdated(address indexed arbitrator, bool allowed);
    event TreasuryUpdated(address indexed treasury);
    event Withdrawn(address indexed account, uint256 amount);

    error AlreadyRegistered();
    error NotRegistered();
    error WalletInUse();
    error InvalidStatus();
    error InvalidStake();
    error InvalidDid();
    error SelfVouch();
    error AlreadyVouched();
    error VoucherNotActive();
    error NotArbitrator();
    error NoChallenge();
    error ZeroAddress();
    error TransferFailed();

    constructor(address initialOwner, address treasury_) Ownable(initialOwner) {
        if (treasury_ == address(0)) revert ZeroAddress();
        treasury = treasury_;
        isArbitrator[initialOwner] = true;
    }

    modifier onlyArbitrator() {
        if (!isArbitrator[msg.sender] && msg.sender != owner()) revert NotArbitrator();
        _;
    }

    // ---------------------------------------------------------------------
    // Registration
    // ---------------------------------------------------------------------

    function register(bytes32 didHash, bytes32 biometricHash) external payable whenNotPaused nonReentrant {
        if (didHash == bytes32(0)) revert InvalidDid();
        if (_humans[didHash].status != Status.None) revert AlreadyRegistered();
        if (walletToDid[msg.sender] != bytes32(0)) revert WalletInUse();
        if (msg.value != registrationStake) revert InvalidStake();

        Human storage human = _humans[didHash];
        human.wallet = msg.sender;
        human.biometricHash = biometricHash;
        human.registeredAt = uint64(block.timestamp);
        human.stake = msg.value;
        human.status = Status.Pending;

        walletToDid[msg.sender] = didHash;
        _dids.push(didHash);
        totalStaked += msg.value;

        emit Registered(didHash, msg.sender, msg.value);

        if (requiredVouches == 0) {
            _activate(didHash, human);
        }
    }

    function vouch(bytes32 didHash) external nonReentrant {
        bytes32 voucherDid = walletToDid[msg.sender];
        if (voucherDid == bytes32(0)) revert NotRegistered();
        if (_humans[voucherDid].status != Status.Active) revert VoucherNotActive();

        Human storage human = _humans[didHash];
        if (human.status != Status.Pending) revert InvalidStatus();
        if (didHash == voucherDid) revert SelfVouch();
        if (hasVouched[didHash][voucherDid]) revert AlreadyVouched();

        hasVouched[didHash][voucherDid] = true;
        _vouchers[didHash].push(voucherDid);
        human.vouchCount += 1;

        emit Vouched(didHash, voucherDid, human.vouchCount);

        if (human.vouchCount >= requiredVouches) {
            _activate(didHash, human);
        }
    }

    function _activate(bytes32 didHash, Human storage human) private {
        human.status = Status.Active;
        human.activeAt = uint64(block.timestamp);
        emit Activated(didHash, human.wallet, human.activeAt);
    }

    // ---------------------------------------------------------------------
    // Challenges
    // ---------------------------------------------------------------------

    function challenge(bytes32 didHash) external payable nonReentrant {
        Human storage human = _humans[didHash];
        if (human.status != Status.Active) revert InvalidStatus();
        if (msg.value != challengeStake) revert InvalidStake();
        if (msg.sender == human.wallet) revert SelfVouch();

        human.status = Status.Challenged;
        human.challenger = msg.sender;
        human.challengeEndsAt = uint64(block.timestamp) + challengeWindow;
        human.challengeDeposit = msg.value;
        totalStaked += msg.value;

        emit Challenged(didHash, msg.sender, msg.value, human.challengeEndsAt);
    }

    /// @notice Resolve a pending challenge. The arbitrator reviews off-chain evidence.
    /// @param didHash Human under challenge.
    /// @param upheld True if the challenge is valid and the human should be revoked.
    function resolveChallenge(bytes32 didHash, bool upheld) external onlyArbitrator nonReentrant {
        Human storage human = _humans[didHash];
        if (human.status != Status.Challenged) revert NoChallenge();

        address challenger = human.challenger;
        uint256 registrationAmount = human.stake;
        uint256 challengeAmount = human.challengeDeposit;

        human.challengeDeposit = 0;
        human.challenger = address(0);
        human.challengeEndsAt = 0;

        if (upheld) {
            uint256 challengerPayout = challengeAmount + (registrationAmount / 2);
            uint256 treasuryCut = registrationAmount - (registrationAmount / 2);

            human.status = Status.Revoked;
            human.stake = 0;

            pendingWithdrawal[challenger] += challengerPayout;
            pendingWithdrawal[treasury] += treasuryCut;
            totalStaked -= (registrationAmount + challengeAmount);

            emit Revoked(didHash, "challenge upheld");
        } else {
            human.status = Status.Active;

            pendingWithdrawal[treasury] += challengeAmount;
            totalStaked -= challengeAmount;
        }

        emit ChallengeResolved(didHash, upheld, challenger);
    }

    /// @notice Emergency revocation by an arbitrator (e.g. fraud ring discovered).
    function revoke(bytes32 didHash, string calldata reason) external onlyArbitrator nonReentrant {
        Human storage human = _humans[didHash];
        if (human.status != Status.Active) revert InvalidStatus();

        uint256 amount = human.stake;
        human.status = Status.Revoked;
        human.stake = 0;
        totalStaked -= amount;
        pendingWithdrawal[treasury] += amount;

        emit Revoked(didHash, reason);
    }

    // ---------------------------------------------------------------------
    // Withdrawals
    // ---------------------------------------------------------------------

    function withdraw() external nonReentrant {
        uint256 amount = pendingWithdrawal[msg.sender];
        if (amount == 0) return;

        pendingWithdrawal[msg.sender] = 0;
        (bool ok, ) = payable(msg.sender).call{value: amount}("");
        if (!ok) revert TransferFailed();

        emit Withdrawn(msg.sender, amount);
    }

    // ---------------------------------------------------------------------
    // Views
    // ---------------------------------------------------------------------

    function getHuman(bytes32 didHash) external view returns (Human memory) {
        return _humans[didHash];
    }

    function getVouchers(bytes32 didHash) external view returns (bytes32[] memory) {
        return _vouchers[didHash];
    }

    function isHuman(address account) external view returns (bool) {
        bytes32 didHash = walletToDid[account];
        return didHash != bytes32(0) && _humans[didHash].status == Status.Active;
    }

    function isHumanDid(bytes32 didHash) external view returns (bool) {
        return _humans[didHash].status == Status.Active;
    }

    function humanCount() external view returns (uint256) {
        return _dids.length;
    }

    function didAt(uint256 index) external view returns (bytes32) {
        return _dids[index];
    }

    // ---------------------------------------------------------------------
    // Admin
    // ---------------------------------------------------------------------

    function setConfig(
        uint256 registrationStake_,
        uint256 challengeStake_,
        uint32 requiredVouches_,
        uint64 challengeWindow_
    ) external onlyOwner {
        registrationStake = registrationStake_;
        challengeStake = challengeStake_;
        requiredVouches = requiredVouches_;
        challengeWindow = challengeWindow_;

        emit ConfigUpdated(registrationStake_, challengeStake_, requiredVouches_, challengeWindow_);
    }

    function setArbitrator(address arbitrator, bool allowed) external onlyOwner {
        if (arbitrator == address(0)) revert ZeroAddress();
        isArbitrator[arbitrator] = allowed;
        emit ArbitratorUpdated(arbitrator, allowed);
    }

    function setTreasury(address treasury_) external onlyOwner {
        if (treasury_ == address(0)) revert ZeroAddress();
        treasury = treasury_;
        emit TreasuryUpdated(treasury_);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }
}
