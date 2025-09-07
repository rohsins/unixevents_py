import unittest
import asyncio
import json
import time
import threading
import os
import sys
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

from unixevents import Linker, create_server, create_client, UnixEventsError, Role


class TestLinkerInitialization(unittest.TestCase):
    """Test Linker initialization and setup"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_channel = f"test_init_{int(time.time() * 1000)}"
        self.cleanup_items = []

    def tearDown(self):
        """Clean up after tests"""
        for item in self.cleanup_items:
            try:
                item.close()
            except:
                pass
        # Clean up any remaining socket files
        for channel in [self.test_channel]:
            socket_path = f"/tmp/{channel}.sock"
            if os.path.exists(socket_path):
                try:
                    os.unlink(socket_path)
                except:
                    pass

    def test_constructor_initialization(self):
        """Test initialization via constructor with both parameters"""
        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)

        self.assertTrue(server._initialized)
        self.assertEqual(server._role, Role.SERVER)
        self.assertEqual(server._channel, self.test_channel)
        self.assertTrue(server._running)

    def test_deferred_initialization(self):
        """Test creating Linker without parameters and initializing later"""
        linker = Linker()
        self.assertFalse(linker._initialized)
        self.assertIsNone(linker._role)

        result = linker.init_sync('server', self.test_channel)
        self.cleanup_items.append(linker)

        self.assertTrue(result)
        self.assertTrue(linker._initialized)
        self.assertEqual(linker._role, Role.SERVER)

    def test_invalid_role_error(self):
        """Test that invalid role raises UnixEventsError"""
        linker = Linker()
        result = linker.init_sync('invalid_role', self.test_channel)
        self.assertFalse(result)  # Should return False on error

    def test_debug_mode(self):
        """Test debug mode functionality"""
        server = Linker('server', self.test_channel, debug=True)
        self.cleanup_items.append(server)

        self.assertTrue(server._debug)

        server.disable_debug()
        self.assertFalse(server._debug)

        server.enable_debug()
        self.assertTrue(server._debug)

    def test_socket_path_creation(self):
        """Test that socket path is created correctly"""
        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)

        expected_path = f"/tmp/{self.test_channel}.sock"
        self.assertEqual(server._socket_path, expected_path)
        self.assertTrue(os.path.exists(expected_path))

    def test_context_manager(self):
        """Test using Linker as a context manager"""
        with Linker('server', self.test_channel) as server:
            self.assertTrue(server._initialized)
            self.assertTrue(server._running)

        # After context, should be closed
        self.assertFalse(server._running)
        self.assertFalse(server._initialized)

    async def test_async_initialization(self):
        """Test async initialization method"""
        linker = Linker()
        result = await linker.init_async('server', self.test_channel, debug=False)
        self.cleanup_items.append(linker)

        self.assertTrue(result)
        self.assertTrue(linker._initialized)
        self.assertEqual(linker._role, Role.SERVER)


class TestServerClientCommunication(unittest.TestCase):
    """Test server-client message passing"""

    def setUp(self):
        self.test_channel = f"test_comm_{int(time.time() * 1000)}"
        self.cleanup_items = []

    def tearDown(self):
        for item in self.cleanup_items:
            try:
                item.close()
            except:
                pass
        # Clean up socket files
        socket_path = f"/tmp/{self.test_channel}.sock"
        if os.path.exists(socket_path):
            try:
                os.unlink(socket_path)
            except:
                pass

    def test_basic_message_passing(self):
        """Test basic server to client and client to server communication"""
        server_received = []
        client_received = []

        # Start server
        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)
        server.receive('test-event', lambda data: server_received.append(data))

        # Allow server to start
        time.sleep(0.1)

        # Start client
        client = Linker('client', self.test_channel)
        self.cleanup_items.append(client)
        client.receive('test-event', lambda data: client_received.append(data))

        # Allow connection to establish
        time.sleep(0.1)

        # Test client to server
        client.send('test-event', 'Hello from client')
        time.sleep(0.1)

        # Test server to client
        server.send('test-event', 'Hello from server')
        time.sleep(0.1)

        # Verify messages received
        self.assertEqual(len(server_received), 1)
        self.assertEqual(server_received[0], 'Hello from client')

        self.assertEqual(len(client_received), 1)
        self.assertEqual(client_received[0], 'Hello from server')

    def test_event_name_prefixing(self):
        """Test that event names are properly prefixed with s- and c-"""
        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)

        # Check that server adds correct prefix
        server.receive('my-event', lambda x: None)
        self.assertIn('c-my-event', server._event_handlers)

        time.sleep(0.1)

        client = Linker('client', self.test_channel)
        self.cleanup_items.append(client)

        # Check that client adds correct prefix
        client.receive('my-event', lambda x: None)
        self.assertIn('s-my-event', client._event_handlers)

    def test_receive_once(self):
        """Test receive_once only fires once"""
        received_count = [0]

        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)

        def handler(data):
            received_count[0] += 1

        server.receive_once('once-test', handler)
        time.sleep(0.1)

        client = Linker('client', self.test_channel)
        self.cleanup_items.append(client)
        time.sleep(0.1)

        # Send multiple messages
        for i in range(3):
            client.send('once-test', f'Message {i}')
            time.sleep(0.05)

        time.sleep(0.2)

        # Should only receive once
        self.assertEqual(received_count[0], 1)

    def test_multiple_handlers_same_event(self):
        """Test multiple handlers for the same event"""
        handler1_data = []
        handler2_data = []

        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)

        server.receive('multi-handler', lambda data: handler1_data.append(data))
        server.receive('multi-handler', lambda data: handler2_data.append(data))

        time.sleep(0.1)

        client = Linker('client', self.test_channel)
        self.cleanup_items.append(client)
        time.sleep(0.1)

        client.send('multi-handler', 'Test data')
        time.sleep(0.1)

        # Both handlers should receive the data
        self.assertEqual(handler1_data, ['Test data'])
        self.assertEqual(handler2_data, ['Test data'])

    def test_multiple_clients(self):
        """Test server broadcasting to multiple clients"""
        client1_received = []
        client2_received = []

        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)
        time.sleep(0.1)

        # Connect first client
        client1 = Linker('client', self.test_channel)
        self.cleanup_items.append(client1)
        client1.receive('broadcast', lambda data: client1_received.append(data))
        time.sleep(0.1)

        # Connect second client
        client2 = Linker('client', self.test_channel)
        self.cleanup_items.append(client2)
        client2.receive('broadcast', lambda data: client2_received.append(data))
        time.sleep(0.1)

        # Server broadcasts
        server.send('broadcast', 'Hello everyone!')
        time.sleep(0.2)

        # Both clients should receive
        self.assertEqual(client1_received, ['Hello everyone!'])
        self.assertEqual(client2_received, ['Hello everyone!'])


class TestDataTypes(unittest.TestCase):
    """Test various data type transmissions"""

    def setUp(self):
        self.test_channel = f"test_types_{int(time.time() * 1000)}"
        self.cleanup_items = []

    def tearDown(self):
        for item in self.cleanup_items:
            try:
                item.close()
            except:
                pass
        socket_path = f"/tmp/{self.test_channel}.sock"
        if os.path.exists(socket_path):
            try:
                os.unlink(socket_path)
            except:
                pass

    def test_string_transmission(self):
        """Test sending string data"""
        received = []

        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)
        server.receive('string-test', lambda data: received.append(data))
        time.sleep(0.1)

        client = Linker('client', self.test_channel)
        self.cleanup_items.append(client)
        time.sleep(0.1)

        test_strings = [
            'Simple string',
            'Unicode: 你好世界 🌍 émojis',
            'Special chars: !@#$%^&*()',
            '',  # Empty string
            'Multi\nline\nstring'
        ]

        for s in test_strings:
            client.send('string-test', s)

        time.sleep(0.2)

        self.assertEqual(received, test_strings)

    def test_dict_transmission(self):
        """Test sending dictionary/JSON data"""
        received = []

        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)
        server.receive('dict-test', lambda data: received.append(data))
        time.sleep(0.1)

        client = Linker('client', self.test_channel)
        self.cleanup_items.append(client)
        time.sleep(0.1)

        test_dict = {
            'string': 'value',
            'number': 42,
            'float': 3.14,
            'boolean': True,
            'null': None,
            'nested': {
                'array': [1, 2, 3],
                'deep': {
                    'level': 3
                }
            }
        }

        client.send('dict-test', test_dict)
        time.sleep(0.1)

        # Note: Based on the code, dicts are JSON stringified in payload
        self.assertEqual(len(received), 1)
        # The received data should be a JSON string of the dict
        self.assertEqual(json.loads(received[0]), test_dict)

    def test_list_transmission(self):
        """Test sending list/array data"""
        received = []

        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)
        server.receive('list-test', lambda data: received.append(data))
        time.sleep(0.1)

        client = Linker('client', self.test_channel)
        self.cleanup_items.append(client)
        time.sleep(0.1)

        test_list = [1, 'two', 3.14, True, None, {'nested': 'dict'}, [1, 2, 3]]

        client.send('list-test', test_list)
        time.sleep(0.1)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0], test_list)

    def test_numeric_transmission(self):
        """Test sending numeric data"""
        received = []

        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)
        server.receive('number-test', lambda data: received.append(data))
        time.sleep(0.1)

        client = Linker('client', self.test_channel)
        self.cleanup_items.append(client)
        time.sleep(0.1)

        test_numbers = [0, 42, -100, 3.14159, -2.718, 1e10, float('inf')]

        for num in test_numbers[:-1]:  # Skip infinity for JSON compatibility
            client.send('number-test', num)

        time.sleep(0.2)

        self.assertEqual(len(received), len(test_numbers) - 1)


class TestCallbacks(unittest.TestCase):
    """Test callback functionality"""

    def setUp(self):
        self.test_channel = f"test_cb_{int(time.time() * 1000)}"
        self.cleanup_items = []

    def tearDown(self):
        for item in self.cleanup_items:
            try:
                item.close()
            except:
                pass
        socket_path = f"/tmp/{self.test_channel}.sock"
        if os.path.exists(socket_path):
            try:
                os.unlink(socket_path)
            except:
                pass

    def test_send_callback_success(self):
        """Test send callback on successful send"""
        callback_called = [False]
        callback_error = [None]
        callback_success = [None]

        def callback(error, success):
            callback_called[0] = True
            callback_error[0] = error
            callback_success[0] = success

        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)
        time.sleep(0.1)

        client = Linker('client', self.test_channel)
        self.cleanup_items.append(client)
        time.sleep(0.1)

        result = client.send('test-event', 'test data', callback)
        time.sleep(0.1)

        self.assertTrue(result)
        self.assertTrue(callback_called[0])
        self.assertIsNone(callback_error[0])
        self.assertTrue(callback_success[0])

    def test_send_callback_failure(self):
        """Test send callback on failure"""
        callback_called = [False]
        callback_error = [None]

        def callback(error, success):
            callback_called[0] = True
            callback_error[0] = error

        # Create uninitialized linker
        linker = Linker()
        result = linker.send('test-event', 'data', callback)

        self.assertFalse(result)
        self.assertTrue(callback_called[0])
        self.assertIsNotNone(callback_error[0])


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""

    def setUp(self):
        self.test_channel = f"test_err_{int(time.time() * 1000)}"
        self.cleanup_items = []

    def tearDown(self):
        for item in self.cleanup_items:
            try:
                item.close()
            except:
                pass
        socket_path = f"/tmp/{self.test_channel}.sock"
        if os.path.exists(socket_path):
            try:
                os.unlink(socket_path)
            except:
                pass

    def test_send_before_init(self):
        """Test sending before initialization returns False"""
        linker = Linker()
        result = linker.send('test', 'data')
        self.assertFalse(result)

    def test_large_message_error(self):
        """Test that oversized messages are rejected"""
        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)
        time.sleep(0.1)

        client = Linker('client', self.test_channel)
        self.cleanup_items.append(client)
        time.sleep(0.1)

        # Create message larger than MAX_MESSAGE_SIZE
        large_data = 'x' * (Linker.MAX_MESSAGE_SIZE + 1000)
        result = client.send('large-event', large_data)

        self.assertFalse(result)

    def test_client_without_server(self):
        """Test client connection when no server exists"""
        linker = Linker()
        result = linker.init_sync('client', f'nonexistent_{time.time()}')
        self.assertFalse(result)  # Should fail to connect

    def test_double_close(self):
        """Test that closing twice doesn't cause errors"""
        server = Linker('server', self.test_channel)
        server.close()
        server.close()  # Should not raise an error

        self.assertFalse(server._running)
        self.assertFalse(server._initialized)

    def test_server_socket_reuse(self):
        """Test that server can reuse socket path after previous server closes"""
        # First server
        server1 = Linker('server', self.test_channel)
        time.sleep(0.1)
        server1.close()
        time.sleep(0.1)

        # Second server should be able to use same channel
        server2 = Linker('server', self.test_channel)
        self.cleanup_items.append(server2)
        self.assertTrue(server2._initialized)


class TestAsyncSupport(unittest.TestCase):
    """Test async/await functionality"""

    def setUp(self):
        self.test_channel = f"test_async_{int(time.time() * 1000)}"
        self.cleanup_items = []

    def tearDown(self):
        for item in self.cleanup_items:
            try:
                item.close()
            except:
                pass
        socket_path = f"/tmp/{self.test_channel}.sock"
        if os.path.exists(socket_path):
            try:
                os.unlink(socket_path)
            except:
                pass

    def test_async_init(self):
        """Test async initialization"""
        async def run_test():
            linker = Linker()
            result = await linker.init_async('server', self.test_channel)
            self.cleanup_items.append(linker)

            self.assertTrue(result)
            self.assertTrue(linker._initialized)
            return linker

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        linker = loop.run_until_complete(run_test())
        loop.close()

    def test_async_send(self):
        """Test async send method"""
        async def run_test():
            server = Linker('server', self.test_channel)
            self.cleanup_items.append(server)
            await asyncio.sleep(0.1)

            client = Linker('client', self.test_channel)
            self.cleanup_items.append(client)
            await asyncio.sleep(0.1)

            result = await client.send_async('test-event', 'async data')
            self.assertTrue(result)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_test())
        loop.close()


class TestPerformance(unittest.TestCase):
    """Performance and stress tests"""

    def setUp(self):
        self.test_channel = f"test_perf_{int(time.time() * 1000)}"
        self.cleanup_items = []

    def tearDown(self):
        for item in self.cleanup_items:
            try:
                item.close()
            except:
                pass
        socket_path = f"/tmp/{self.test_channel}.sock"
        if os.path.exists(socket_path):
            try:
                os.unlink(socket_path)
            except:
                pass

    def test_message_throughput(self):
        """Test high-volume message throughput"""
        message_count = 1000
        received_count = [0]

        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)

        def handler(data):
            received_count[0] += 1

        server.receive('perf-test', handler)
        time.sleep(0.1)

        client = Linker('client', self.test_channel)
        self.cleanup_items.append(client)
        time.sleep(0.1)

        start_time = time.time()

        # Send many messages rapidly
        for i in range(message_count):
            client.send('perf-test', {'index': i})

        # Wait for all messages with timeout
        timeout = 10
        start_wait = time.time()
        while received_count[0] < message_count and time.time() - start_wait < timeout:
            time.sleep(0.01)

        elapsed = time.time() - start_time

        self.assertEqual(received_count[0], message_count)

        messages_per_second = message_count / elapsed
        print(f"\nThroughput: {messages_per_second:.0f} messages/second")
        self.assertGreater(messages_per_second, 100)  # Minimum performance threshold

    def test_concurrent_sends(self):
        """Test concurrent sending from multiple threads"""
        received_messages = []
        lock = threading.Lock()

        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)

        def handler(data):
            with lock:
                received_messages.append(data)

        server.receive('concurrent-test', handler)
        time.sleep(0.1)

        client = Linker('client', self.test_channel)
        self.cleanup_items.append(client)
        time.sleep(0.1)

        # Send from multiple threads
        def send_messages(thread_id):
            for i in range(10):
                client.send('concurrent-test', f'Thread-{thread_id}-Message-{i}')
                time.sleep(0.01)

        threads = []
        for i in range(5):
            t = threading.Thread(target=send_messages, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        time.sleep(0.5)

        # Should receive all 50 messages
        self.assertEqual(len(received_messages), 50)


class TestNodeJsCompatibility(unittest.TestCase):
    """Test compatibility with Node.js implementation"""

    @classmethod
    def setUpClass(cls):
        """Check if Node.js is available"""
        try:
            result = subprocess.run(['node', '--version'], 
                                    capture_output=True, 
                                    text=True)
            cls.node_available = result.returncode == 0
        except:
            cls.node_available = False

    def setUp(self):
        self.test_channel = f"test_node_{int(time.time() * 1000)}"
        self.cleanup_items = []

    def tearDown(self):
        for item in self.cleanup_items:
            try:
                item.close()
            except:
                pass
        socket_path = f"/tmp/{self.test_channel}.sock"
        if os.path.exists(socket_path):
            try:
                os.unlink(socket_path)
            except:
                pass

    @unittest.skipUnless('node_available' in dir() and node_available, 
                         "Node.js not available")
    def test_message_format_compatibility(self):
        """Test that message format is compatible with Node.js version"""
        # This test would require the actual Node.js unixevents library
        # For now, we'll test the message format

        server = Linker('server', self.test_channel)
        self.cleanup_items.append(server)

        received_raw = []

        # Monkey-patch to capture raw message
        original_process = server._process_message
        def capture_process(message):
            received_raw.append(message)
            return original_process(message)
        server._process_message = capture_process

        time.sleep(0.1)

        client = Linker('client', self.test_channel)
        self.cleanup_items.append(client)
        time.sleep(0.1)

        client.send('test-event', {'key': 'value'})
        time.sleep(0.1)

        # Verify message format
        self.assertEqual(len(received_raw), 1)
        msg = json.loads(received_raw[0].decode('utf-8'))

        self.assertIn('event', msg)
        self.assertIn('payload', msg)
        self.assertEqual(msg['event'], 'c-test-event')  # Client prefix


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions"""

    def setUp(self):
        self.test_channel = f"test_helper_{int(time.time() * 1000)}"
        self.cleanup_items = []

    def tearDown(self):
        for item in self.cleanup_items:
            try:
                item.close()
            except:
                pass
        socket_path = f"/tmp/{self.test_channel}.sock"
        if os.path.exists(socket_path):
            try:
                os.unlink(socket_path)
            except:
                pass

    def test_create_server(self):
        """Test create_server helper function"""
        server = create_server(self.test_channel)
        self.cleanup_items.append(server)

        self.assertIsInstance(server, Linker)
        self.assertEqual(server._role, Role.SERVER)
        self.assertTrue(server._initialized)

    def test_create_client(self):
        """Test create_client helper function"""
        server = create_server(self.test_channel)
        self.cleanup_items.append(server)
        time.sleep(0.1)

        client = create_client(self.test_channel)
        self.cleanup_items.append(client)

        self.assertIsInstance(client, Linker)
        self.assertEqual(client._role, Role.CLIENT)
        self.assertTrue(client._initialized)


if __name__ == '__main__':
    # Run tests with verbosity
    unittest.main(verbosity=2)
