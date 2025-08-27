#!/usr/bin/env python3
"""
UnixEvents Python Examples
Demonstrates usage patterns equivalent to the JavaScript examples.
"""

import asyncio
import threading
import time
from unixevents import UnixEvents, Linker


def example1_server():
    """
    Example 1 - Server Program
    Equivalent to the first JavaScript example
    """
    print("=== Example 1: Server Program ===")

    # Create server instance
    server = UnixEvents('server', 'Channel1')

    # Set up event listener
    def on_event_s_a(data):
        print(f'Message on server: {data}')

    server.receive('event-s-a', on_event_s_a)

    # Send message after 100ms
    def send_delayed():
        time.sleep(0.1)
        server.send('event-c-a', 'Mesg from server')

    threading.Thread(target=send_delayed, daemon=True).start()

    # Close after 1 second
    def close_delayed():
        time.sleep(1.0)
        server.close()

    threading.Thread(target=close_delayed, daemon=True).start()

    # Keep running until closed
    time.sleep(1.1)


def example1_client():
    """
    Example 1 - Client Program  
    Equivalent to the first JavaScript example
    """
    print("=== Example 1: Client Program ===")

    # Wait a bit for server to start
    time.sleep(0.05)

    # Create client instance
    client = UnixEvents('client', 'Channel1')

    # Set up event listener
    def on_event_c_a(data):
        print(f'Message on client: {data}')

    client.receive('event-c-a', on_event_c_a)

    # Send message after 100ms
    def send_delayed():
        time.sleep(0.1)
        client.send('event-s-a', 'Mesg from client')

    threading.Thread(target=send_delayed, daemon=True).start()

    # Close after 1 second
    def close_delayed():
        time.sleep(1.0)
        client.close()

    threading.Thread(target=close_delayed, daemon=True).start()

    # Keep running until closed
    time.sleep(1.1)


async def example2_server():
    """
    Example 2 - Async Server Program
    Equivalent to the async JavaScript example
    """
    print("=== Example 2: Async Server Program ===")

    server = UnixEvents()
    result = await server.init('server', 'Channel2')
    print(f"server initialized: {result}")

    def on_event_sa(data):
        print(f'Message on server: {data}')

    server.receive('event-sa', on_event_sa)

    # Send message
    server.send('event-ca', 'Mesg from server')

    # Close after short delay
    await asyncio.sleep(0.1)
    server.close()


async def example2_client():
    """
    Example 2 - Async Client Program
    Equivalent to the async JavaScript example  
    """
    print("=== Example 2: Async Client Program ===")

    # Wait for server
    await asyncio.sleep(0.01)

    client = UnixEvents()
    result = await client.init('client', 'channel2')  # Note: case insensitive
    print(f"client initialized: {result}")

    def on_event_ca(data):
        print(f'Message on client: {data}')

    client.receive('event-ca', on_event_ca)

    # Send message
    client.send('event-sa', 'Mesg from client')

    # Close after short delay
    await asyncio.sleep(0.1)
    client.close()


def example3_advanced():
    """
    Example 3 - Advanced Usage
    Demonstrates additional features like receive_once and sync sending
    """
    print("=== Example 3: Advanced Usage ===")

    # Server setup
    server = Linker('server', 'AdvancedChannel')

    # Client setup (with slight delay)
    def setup_client():
        time.sleep(0.05)
        client = Linker('client', 'AdvancedChannel')

        # Regular event listener
        def on_regular_event(data):
            print(f'Client regular event: {data}')

        # One-time event listener
        def on_once_event(data):
            print(f'Client once event (will only fire once): {data}')

        client.receive('regular-event', on_regular_event)
        client.receive_once('once-event', on_once_event)

        # Send some test events
        client.send('server-regular', 'Regular message 1')
        client.send('server-regular', 'Regular message 2')
        client.send('server-once', 'Once message 1')
        client.send('server-once', 'Once message 2')  # This should also trigger

        # Close client after delay
        time.sleep(0.5)
        client.close()

    # Server event handlers
    def on_server_regular(data):
        print(f'Server regular event: {data}')
        # Echo back
        server.send('regular-event', f'Echo: {data}')

    def on_server_once(data):
        print(f'Server once event (first time only): {data}')
        # Send once event to client
        server.send('once-event', f'Once response: {data}')

    server.receive('server-regular', on_server_regular)
    server.receive_once('server-once', on_server_once)

    # Start client in separate thread
    client_thread = threading.Thread(target=setup_client, daemon=True)
    client_thread.start()

    # Keep server running
    time.sleep(1.0)
    server.close()
    client_thread.join(timeout=1.0)


async def example4_sync_async():
    """
    Example 4 - Synchronous vs Asynchronous Sending
    Demonstrates the difference between send() and send_sync()
    """
    print("=== Example 4: Sync vs Async Sending ===")

    # Setup
    server = UnixEvents('server', 'SyncAsyncChannel')

    async def client_task():
        await asyncio.sleep(0.05)  # Wait for server
        client = UnixEvents('client', 'SyncAsyncChannel')

        def on_message(data):
            print(f'Client received: {data}')

        client.receive('test-event', on_message)

        # Async send with callback
        def send_callback(error, success):
            if error:
                print(f'Send failed: {error}')
            else:
                print(f'Async send successful: {success}')

        client.send('server-event', 'Async message', send_callback)

        # Sync send
        success = await client.send_sync('server-event', 'Sync message')
        print(f'Sync send result: {success}')

        await asyncio.sleep(0.2)
        client.close()

    # Server handlers
    def on_server_event(data):
        print(f'Server received: {data}')
        server.send('test-event', f'Response to: {data}')

    server.receive('server-event', on_server_event)

    # Run client
    await client_task()

    server.close()


def run_example_1():
    """Run the first example with both server and client."""
    print("Running Example 1...")

    server_thread = threading.Thread(target=example1_server, daemon=True)
    client_thread = threading.Thread(target=example1_client, daemon=True)

    server_thread.start()
    client_thread.start()

    server_thread.join()
    client_thread.join()
    print()


async def run_example_2():
    """Run the async example."""
    print("Running Example 2...")

    # Run server and client concurrently
    await asyncio.gather(
        example2_server(),
        example2_client()
    )
    print()


def run_example_3():
    """Run the advanced example."""
    print("Running Example 3...")
    example3_advanced()
    print()


async def run_example_4():
    """Run the sync/async example."""
    print("Running Example 4...")
    await example4_sync_async()
    print()


async def main():
    """Run all examples."""
    print("UnixEvents Python Port - Examples\n")

    # Example 1: Basic usage
    run_example_1()

    # Example 2: Async initialization  
    await run_example_2()

    # Example 3: Advanced features
    run_example_3()

    # Example 4: Sync vs Async
    await run_example_4()

    print("All examples completed!")


if __name__ == "__main__":
    # You can run individual examples or all of them
    import sys

    if len(sys.argv) > 1:
        example_num = sys.argv[1]

        if example_num == "1":
            run_example_1()
        elif example_num == "2":
            asyncio.run(run_example_2())
        elif example_num == "3":
            run_example_3()
        elif example_num == "4":
            asyncio.run(run_example_4())
        else:
            print("Available examples: 1, 2, 3, 4")
    else:
        # Run all examples
        asyncio.run(main())

