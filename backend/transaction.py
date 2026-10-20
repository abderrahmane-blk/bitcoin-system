import time

class Transaction:
    """
    Represents a simple transaction in the blockchain.
    
    Attributes:
        sender (str): The sender's address or identifier.
        receivers (dict): Dictionary of {receiver_address: amount}.
        amount (float): The total amount being transferred.
        timestamp (float): The time when the transaction was created (Unix timestamp).
    """
    
    def __init__(self, sender: str, receivers: dict, amount: float):
        self.sender = sender
        self.receivers = receivers
        self.amount = amount
        self.timestamp = time.time()  # Auto-generate timestamp
        
        # Validation: Verify that sum of outputs equals total amount
        total_output = sum(receivers.values())
        if abs(total_output - amount) > 1e-9:  # Float comparison tolerance
            raise ValueError(f"Transaction amount mismatch: {amount} != sum(receivers) {total_output}")

    def to_dict(self) -> dict:
        """
        Returns a dictionary representation of the transaction.
        """
        return {
            'sender': self.sender,
            'receivers': self.receivers,
            'amount': self.amount,
            'timestamp': self.timestamp
        }
    

    def to_string(self) -> str:
        """
        Returns a concatenated string representation of all fields for hashing purposes.

        This concatenates sender, sorted receivers, amount (as str), and timestamp (as str).

        Timestamp is truncated to whole seconds to allow slight network delays.
        """
        # Sort receivers by address to ensure deterministic hashing
        sorted_receivers = sorted(self.receivers.items())
        receivers_str = "".join([f"{k}{v}" for k, v in sorted_receivers])
        
        timestamp_truncated = int(self.timestamp)  # Truncate to whole seconds
        return f"{self.sender}{receivers_str}{self.amount}{timestamp_truncated}"


    def __repr__(self) -> str:
        return (f"Transaction(sender='{self.sender}', receivers={self.receivers}, "
                f"amount={self.amount}, timestamp={self.timestamp})")



# Test the Transaction class (can be run directly for quick testing)
if __name__ == "__main__":
    tx = Transaction(sender="Alice", receivers={"Bob": 10.5}, amount=10.5)
    
    print(tx)
    
    print("Dictionary representation:", tx.to_dict())
    
    # Print string for hashing purposes
    print("String for hashing:", tx.to_string())