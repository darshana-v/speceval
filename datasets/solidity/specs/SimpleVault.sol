// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SimpleVault {
    address public owner;
    bool public locked;

    constructor() {
        owner = msg.sender;
        locked = false;
    }

    function lock() external {
        require(msg.sender == owner, "Only owner");
        require(!locked, "Already locked");
        locked = true;
        assert(locked == true);
    }

    function unlock() external {
        require(msg.sender == owner, "Only owner");
        require(locked, "Not locked");
        locked = false;
        assert(locked == false);
    }

    function emergencyWithdraw() external {
        require(msg.sender == owner, "Only owner");
        require(!locked, "Vault is locked");

        uint256 bal = address(this).balance;
        (bool ok, ) = owner.call{value: bal}("");
        if (!ok) revert();
    }

    receive() external payable {}
}
