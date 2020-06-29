{
    "foreign": true,
    "real_name": "std::posix::network",
    "fns": [
        {
            "arity": 0,
            "name": "socket",
            "real_name": "Std::Posix::Network::socket",
            "bytecode_name": "std::posix::network::socket",
            "from_module": "Std::Posix::Network",
            "params": []
        },
        {
            "arity": 3,
            "name": "connect",
            "real_name": "Std::Posix::Network::connect",
            "bytecode_name": "std::posix::network::connect",
            "from_module": "Std::Posix::Network",
            "params": [ "sock", "~addr", "~port" ]
        },
        {
            "arity": 3,
            "name": "bind",
            "real_name": "Std::Posix::Network::bind",
            "bytecode_name": "std::posix::network::bind",
            "from_module": "Std::Posix::Network",
            "params": [ "sock", "~addr", "~port" ]
        },
        {
            "arity": 2,
            "name": "listen",
            "real_name": "Std::Posix::Network::listen",
            "bytecode_name": "std::posix::network::listen",
            "from_module": "Std::Posix::Network",
            "params": [ "sock", "~backlog" ]
        },
        {
            "arity": 1,
            "name": "accept",
            "real_name": "Std::Posix::Network::accept",
            "bytecode_name": "std::posix::network::accept",
            "from_module": "Std::Posix::Network",
            "params": [ "sock" ]
        },
        {
            "arity": 2,
            "name": "write",
            "real_name": "Std::Posix::Network::write",
            "bytecode_name": "std::posix::network::write",
            "from_module": "Std::Posix::Network",
            "params": [ "sock", "buffer" ]
        },
        {
            "arity": 1,
            "name": "read",
            "real_name": "Std::Posix::Network::read",
            "bytecode_name": "std::posix::network::read",
            "from_module": "Std::Posix::Network",
            "params": [ "sock" ]
        },
        {
            "arity": 2,
            "name": "recv",
            "real_name": "Std::Posix::Network::recv",
            "bytecode_name": "std::posix::network::recv",
            "from_module": "Std::Posix::Network",
            "params": [ "sock", "~count" ]
        },
        {
            "arity": 1,
            "name": "shutdown",
            "real_name": "Std::Posix::Network::shutdown",
            "bytecode_name": "std::posix::network::shutdown",
            "from_module": "Std::Posix::Network",
            "params": [ "sock" ]
        },
        {
            "arity": 1,
            "name": "close",
            "real_name": "Std::Posix::Network::close",
            "bytecode_name": "std::posix::network::close",
            "from_module": "Std::Posix::Network",
            "params": [ "sock" ]
        }
    ],
    "enums": {}
}
