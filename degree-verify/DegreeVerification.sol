// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * DegreeVerification — minimal FY project contract
 * Only two functions that matter for a viva demo:
 *   issueDegree()  → university stores a hash
 *   verifyDegree() → employer checks a hash
 */
contract DegreeVerification {

    address public owner;
    uint256 public totalIssued;

    // hash → studentId  (only stored so owner can look it up)
    mapping(bytes32 => string) private registry;
    mapping(bytes32 => bool)   private issued;
    mapping(bytes32 => bool)   private revoked;

    event Issued (bytes32 indexed hash, string studentId, uint256 when);
    event Revoked(bytes32 indexed hash, uint256 when);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorised");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    // University calls this after uploading the PDF
    function issueDegree(bytes32 _hash, string calldata _studentId) external onlyOwner {
        require(!issued[_hash],           "Already registered");
        require(bytes(_studentId).length > 0, "Student ID required");
        registry[_hash]  = _studentId;
        issued[_hash]    = true;
        totalIssued     += 1;
        emit Issued(_hash, _studentId, block.timestamp);
    }

    // Employer calls this — returns (valid, revoked)
    function verifyDegree(bytes32 _hash) external view returns (bool, bool) {
        if (!issued[_hash])  return (false, false);
        if (revoked[_hash])  return (false, true);
        return (true, false);
    }

    // University can revoke a fraudulent degree
    function revokeDegree(bytes32 _hash) external onlyOwner {
        require(issued[_hash],   "Not found");
        require(!revoked[_hash], "Already revoked");
        revoked[_hash] = true;
        emit Revoked(_hash, block.timestamp);
    }

    // Internal lookup — owner only
    function getStudentId(bytes32 _hash) external view onlyOwner returns (string memory) {
        require(issued[_hash], "Not found");
        return registry[_hash];
    }
}
