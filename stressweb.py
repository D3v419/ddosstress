import requests
import time
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import argparse

class PacketSender:
    def __init__(self, url, num_packets=1000000, concurrency=100, method='GET', data=None, headers=None):
        self.url = url
        self.num_packets = num_packets
        self.concurrency = concurrency
        self.method = method.upper()
        self.data = data
        self.headers = headers or {"User-Agent": "StressTest/1.0"}
        self.sent_packets = 0
        self.success_packets = 0
        self.failed_packets = 0
        self.start_time = None
        self.end_time = None

    def send_single_packet(self):
        """Send a single packet using requests library"""
        try:
            if self.method == 'GET':
                response = requests.get(self.url, headers=self.headers, timeout=5)
            elif self.method == 'POST':
                response = requests.post(self.url, data=self.data, headers=self.headers, timeout=5)
            
            if response.status_code < 400:
                return True
            return False
        except Exception:
            return False

    def send_packets_threaded(self):
        """Send packets using threading for concurrency"""
        self.start_time = time.time()
        print(f"Starting packet transmission to {self.url}")
        print(f"Sending {self.num_packets} packets with {self.concurrency} concurrent connections")
        
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            results = list(executor.map(lambda _: self.send_single_packet(), range(self.num_packets)))
        
        self.sent_packets = self.num_packets
        self.success_packets = sum(results)
        self.failed_packets = self.num_packets - self.success_packets
        self.end_time = time.time()
        self.print_stats()

    async def send_single_packet_async(self, session):
        """Send a single packet using aiohttp"""
        try:
            if self.method == 'GET':
                async with session.get(self.url, headers=self.headers, timeout=5) as response:
                    return response.status < 400
            elif self.method == 'POST':
                async with session.post(self.url, data=self.data, headers=self.headers, timeout=5) as response:
                    return response.status < 400
        except Exception:
            return False

    async def send_batch_async(self, batch_size=10000):
        """Send packets in batches to avoid memory issues"""
        self.start_time = time.time()
        print(f"Starting async packet transmission to {self.url}")
        print(f"Sending {self.num_packets} packets with {self.concurrency} concurrent connections")
        
        connector = aiohttp.TCPConnector(limit=self.concurrency)
        async with aiohttp.ClientSession(connector=connector) as session:
            for i in range(0, self.num_packets, batch_size):
                current_batch = min(batch_size, self.num_packets - i)
                tasks = [self.send_single_packet_async(session) for _ in range(current_batch)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                self.sent_packets += current_batch
                self.success_packets += sum(1 for r in results if r is True)
                self.failed_packets += sum(1 for r in results if r is not True)
                
                # Print progress
                print(f"Progress: {self.sent_packets}/{self.num_packets} packets sent "
                      f"({(self.sent_packets/self.num_packets*100):.2f}%)")
        
        self.end_time = time.time()
        self.print_stats()

    def print_stats(self):
        """Print statistics about the packet sending operation"""
        duration = self.end_time - self.start_time
        packets_per_second = self.sent_packets / duration if duration > 0 else 0
        
        print("\n===== Packet Sending Statistics =====")
        print(f"Target URL: {self.url}")
        print(f"Total packets sent: {self.sent_packets}")
        print(f"Successful packets: {self.success_packets} ({self.success_packets/self.sent_packets*100:.2f}%)")
        print(f"Failed packets: {self.failed_packets} ({self.failed_packets/self.sent_packets*100:.2f}%)")
        print(f"Total time: {duration:.2f} seconds")
        print(f"Average speed: {packets_per_second:.2f} packets/second")
        print("====================================")


async def main():
    parser = argparse.ArgumentParser(description="HTTP Packet Stress Testing Tool")
    parser.add_argument("url", help="Target URL to send packets to")
    parser.add_argument("-n", "--num-packets", type=int, default=1000000, help="Number of packets to send (default: 1,000,000)")
    parser.add_argument("-c", "--concurrency", type=int, default=100, help="Number of concurrent connections (default: 100)")
    parser.add_argument("-m", "--method", choices=["GET", "POST"], default="GET", help="HTTP method to use (default: GET)")
    parser.add_argument("-d", "--data", help="Data to send with POST requests")
    parser.add_argument("-b", "--batch-size", type=int, default=10000, help="Batch size for async sending (default: 10,000)")
    args = parser.parse_args()
    
    sender = PacketSender(
        url=args.url,
        num_packets=args.num_packets,
        concurrency=args.concurrency,
        method=args.method,
        data=args.data
    )
    
    # Use async version for better performance with large number of packets
    await sender.send_batch_async(batch_size=args.batch_size)


if __name__ == "__main__":
    print("HTTP Packet Stress Testing Tool")
    print("WARNING: This tool should only be used on systems you own or have permission to test.")
    print("Improper use may be illegal and/or cause service disruption.\n")
    
    # Run the async main function
    asyncio.run(main())