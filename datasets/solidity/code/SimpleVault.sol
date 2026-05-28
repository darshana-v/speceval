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
        locked = true;
    }

    function unlock() external {
        locked = false;
    }

    function emergencyWithdraw() external {
        (bool ok, ) = owner.call{value: address(this).balance}("");
        if (!ok) revert();
    }

    receive() external payable {}
}
