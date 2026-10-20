# peer.py
import uuid
from typing import Optional

class Peer:
    """
    Represents a peer node in the blockchain network
    """
    
    def __init__(self, name: str, port: int, host: str = "127.0.0.1", peer_uuid: Optional[str] = None):
        self.name = name
        self.port = port
        self.host = host
        self.uuid = peer_uuid if peer_uuid else str(uuid.uuid4())
        self.url = f"http://{self.host}:{self.port}"
        self.is_alive = True  # Track if peer is responsive
        self.last_seen = None  # Timestamp of last communication
    
    def to_dict(self) -> dict:
        """Convert peer to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "uuid": self.uuid,
            "host": self.host,
            "port": self.port,
            "url": self.url,
            "is_alive": self.is_alive
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Peer':
        """Create Peer object from dictionary"""
        peer = cls(
            name=data["name"],
            port=data["port"],
            host=data.get("host", "127.0.0.1"),
            peer_uuid=data.get("uuid")
        )
        peer.is_alive = data.get("is_alive", True)
        return peer
    
    def __repr__(self) -> str:
        return f"Peer(name='{self.name}', uuid='{self.uuid[:8]}...', url='{self.url}')"
    
    def __eq__(self, other) -> bool:
        """Compare peers by UUID"""
        if isinstance(other, Peer):
            return self.uuid == other.uuid
        return False
    
    def __hash__(self):
        """Make Peer hashable so it can be used in sets"""
        return hash(self.uuid)


# Test
if __name__ == "__main__":
    peer1 = Peer("Alice", 8001)
    peer2 = Peer("Bob", 8002)
    
    print(peer1)
    print(peer1.to_dict())
    
    # Test from_dict
    peer3 = Peer.from_dict(peer1.to_dict())
    print(f"Recreated: {peer3}")
    print(f"Equal? {peer1 == peer3}")