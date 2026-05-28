// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SafeTransfer {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function transfer(address to, uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        require(to != address(0), "Transfer to zero address");
        require(to != msg.sender, "Self-transfer");

        balances[msg.sender] -= amount;
        balances[to] += amount;

        assert(balances[msg.sender] >= 0);
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");

        balances[msg.sender] -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        if (!ok) revert();
    }
}
