"""
Proxy Manager — Round-robin proxy rotation with blacklist.
"""

import random
import time
import requests
from typing import List, Dict, Optional

class ProxyManager:
    def __init__(self, proxies: List[str] = None):
        self.proxies = proxies or []
        self.blacklist = set()
        self.current_index = 0
        self.proxy_stats = {}
        
        # Initialize stats for each proxy
        for proxy in self.proxies:
            self.proxy_stats[proxy] = {
                "success": 0,
                "fail": 0,
                "last_used": 0
            }
    
    def add_proxy(self, proxy: str):
        """Add proxy to pool"""
        if proxy not in self.proxies:
            self.proxies.append(proxy)
            self.proxy_stats[proxy] = {
                "success": 0,
                "fail": 0,
                "last_used": 0
            }
            print(f"Added proxy: {proxy}")
    
    def remove_proxy(self, proxy: str):
        """Remove proxy from pool"""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            if proxy in self.proxy_stats:
                del self.proxy_stats[proxy]
            print(f"Removed proxy: {proxy}")
    
    def blacklist_proxy(self, proxy: str, reason: str = "failed"):
        """Blacklist a proxy"""
        self.blacklist.add(proxy)
        print(f"Blacklisted proxy: {proxy} ({reason})")
    
    def get_proxy(self) -> Optional[str]:
        """Get next proxy (round-robin)"""
        if not self.proxies:
            return None
        
        # Filter out blacklisted proxies
        available = [p for p in self.proxies if p not in self.blacklist]
        
        if not available:
            print("All proxies blacklisted, resetting blacklist...")
            self.blacklist.clear()
            available = self.proxies
        
        if not available:
            return None
        
        # Round-robin selection
        proxy = available[self.current_index % len(available)]
        self.current_index += 1
        
        # Update stats
        self.proxy_stats[proxy]["last_used"] = time.time()
        
        return proxy
    
    def get_random_proxy(self) -> Optional[str]:
        """Get random proxy"""
        available = [p for p in self.proxies if p not in self.blacklist]
        
        if not available:
            print("All proxies blacklisted, resetting blacklist...")
            self.blacklist.clear()
            available = self.proxies
        
        if not available:
            return None
        
        proxy = random.choice(available)
        self.proxy_stats[proxy]["last_used"] = time.time()
        
        return proxy
    
    def get_best_proxy(self) -> Optional[str]:
        """Get proxy with highest success rate"""
        available = [p for p in self.proxies if p not in self.blacklist]
        
        if not available:
            return self.get_proxy()
        
        # Sort by success rate
        def success_rate(p):
            stats = self.proxy_stats[p]
            total = stats["success"] + stats["fail"]
            return stats["success"] / total if total > 0 else 0.5
        
        available.sort(key=success_rate, reverse=True)
        proxy = available[0]
        self.proxy_stats[proxy]["last_used"] = time.time()
        
        return proxy
    
    def report_success(self, proxy: str):
        """Report successful use of proxy"""
        if proxy in self.proxy_stats:
            self.proxy_stats[proxy]["success"] += 1
    
    def report_failure(self, proxy: str, blacklist_after: int = 3):
        """Report failed use of proxy"""
        if proxy in self.proxy_stats:
            self.proxy_stats[proxy]["fail"] += 1
            
            # Blacklist after multiple failures
            if self.proxy_stats[proxy]["fail"] >= blacklist_after:
                self.blacklist_proxy(proxy, f"failed {blacklist_after} times")
    
    def get_proxy_dict(self, proxy: str) -> Dict[str, str]:
        """Convert proxy string to requests format"""
        if not proxy:
            return {}
        
        return {
            "http": proxy,
            "https": proxy
        }
    
    def get_stats(self) -> Dict:
        """Get proxy pool statistics"""
        return {
            "total": len(self.proxies),
            "available": len([p for p in self.proxies if p not in self.blacklist]),
            "blacklisted": len(self.blacklist),
            "stats": self.proxy_stats
        }
    
    def load_from_file(self, filepath: str):
        """Load proxies from file (one per line)"""
        try:
            with open(filepath, 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]
            
            for proxy in proxies:
                self.add_proxy(proxy)
            
            print(f"Loaded {len(proxies)} proxies from {filepath}")
            
        except Exception as e:
            print(f"Error loading proxies: {e}")
    
    def load_from_list(self, proxy_list: List[str]):
        """Load proxies from list"""
        for proxy in proxy_list:
            self.add_proxy(proxy)

if __name__ == "__main__":
    # Test proxy manager
    manager = ProxyManager()
    
    # Add test proxies
    manager.add_proxy("http://user:pass@proxy1:8080")
    manager.add_proxy("http://user:pass@proxy2:8080")
    manager.add_proxy("http://user:pass@proxy3:8080")
    
    # Get proxies
    for i in range(5):
        proxy = manager.get_proxy()
        print(f"Proxy {i+1}: {proxy}")
    
    # Report success/failure
    manager.report_success("http://user:pass@proxy1:8080")
    manager.report_success("http://user:pass@proxy1:8080")
    manager.report_failure("http://user:pass@proxy2:8080")
    
    # Get stats
    stats = manager.get_stats()
    print(f"\nStats: {stats}")
