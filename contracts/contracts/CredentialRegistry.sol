// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title CredentialRegistry
/// @notice Anchors hashed verifiable credentials on-chain. Contents live off-chain
///         (encrypted IPFS), so no PII is written to the ledger.
contract CredentialRegistry is Ownable {
    struct Credential {
        bytes32 subjectDid;
        bytes32 schemaId;
        bytes32 contentHash;
        address issuer;
        uint64 issuedAt;
        uint64 expiresAt;
        bool revoked;
        string cid;
    }

    mapping(bytes32 => Credential) private _credentials;
    mapping(bytes32 => bytes32[]) private _bySubject;
    mapping(address => bool) public isIssuer;
    uint256 private _nonce;

    event Issued(
        bytes32 indexed credentialId,
        bytes32 indexed subjectDid,
        bytes32 indexed schemaId,
        address issuer,
        string cid
    );
    event Revoked(bytes32 indexed credentialId, address indexed issuer, string reason);
    event IssuerUpdated(address indexed issuer, bool allowed);

    error NotIssuer();
    error UnknownCredential();
    error InvalidSubject();
    error InvalidExpiry();
    error ZeroAddress();

    constructor(address initialOwner) Ownable(initialOwner) {
        isIssuer[initialOwner] = true;
    }

    modifier onlyIssuer() {
        if (!isIssuer[msg.sender] && msg.sender != owner()) revert NotIssuer();
        _;
    }

    function issue(
        bytes32 subjectDid,
        bytes32 schemaId,
        bytes32 contentHash,
        uint64 expiresAt,
        string calldata cid
    ) external onlyIssuer returns (bytes32 credentialId) {
        if (subjectDid == bytes32(0)) revert InvalidSubject();
        if (expiresAt != 0 && expiresAt <= block.timestamp) revert InvalidExpiry();

        credentialId = keccak256(
            abi.encode(
                subjectDid,
                schemaId,
                contentHash,
                block.chainid,
                address(this),
                _nonce++
            )
        );

        _credentials[credentialId] = Credential({
            subjectDid: subjectDid,
            schemaId: schemaId,
            contentHash: contentHash,
            issuer: msg.sender,
            issuedAt: uint64(block.timestamp),
            expiresAt: expiresAt,
            revoked: false,
            cid: cid
        });

        _bySubject[subjectDid].push(credentialId);

        emit Issued(credentialId, subjectDid, schemaId, msg.sender, cid);
    }

    function revoke(bytes32 credentialId, string calldata reason) external {
        Credential storage credential = _credentials[credentialId];
        if (credential.issuer == address(0)) revert UnknownCredential();
        if (credential.issuer != msg.sender && msg.sender != owner()) revert NotIssuer();

        credential.revoked = true;
        emit Revoked(credentialId, msg.sender, reason);
    }

    function isValid(bytes32 credentialId) external view returns (bool) {
        Credential storage credential = _credentials[credentialId];
        if (credential.issuer == address(0) || credential.revoked) return false;
        if (credential.expiresAt != 0 && credential.expiresAt <= block.timestamp) return false;
        return true;
    }

    function getCredential(bytes32 credentialId) external view returns (Credential memory) {
        return _credentials[credentialId];
    }

    function getSubjectCredentials(bytes32 subjectDid) external view returns (bytes32[] memory) {
        return _bySubject[subjectDid];
    }

    function setIssuer(address issuer, bool allowed) external onlyOwner {
        if (issuer == address(0)) revert ZeroAddress();
        isIssuer[issuer] = allowed;
        emit IssuerUpdated(issuer, allowed);
    }
}
