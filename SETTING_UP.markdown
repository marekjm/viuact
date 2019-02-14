# Setting up the environment

Create a directory in which both Viua VM source tree and Viuact source tree will
be kept, and enter it:

```
$ mkdir ~/viuact-workspace
$ cd ~/viuact-workspace
```

Then clone Viuact and Viua VM repositories:

```
$ git clone inz@viuavm.org:/home/inz/git/viuact.git
$ git clone git@git.sr.ht:~maelkum/viuavm
```

Then compile Viua VM on the `devel` branch:

```
$ cd ~/viuact-workspace/viuavm
$ git checkout devel
$ make -j 4
```

Then enter Viuact source tree directory and prepare the environment by exporting
the necessary environment variables:

```
$ cd ~/viuact-workspace/viuact
$ export VIUA_ASM_PATH=../viuavm/build/bin/vm/asm
$ export VIUA_VM_KERNEL_PATH=../viuavm/build/bin/vm/kernel
$ export VIUA_LIBRARY_PATH=../viuavm/build/stdlib
$ export VIUAC_LIBRARY_PATH=../viuavm/build/stdlib
```

----

## Confirm it's working

Open two terminal emulators.
After exporting the necessary variables in both of them, run the server in the
first one:

```
$ bash ./ex/chat_server.sh make
$ VIUA_FFI_SCHEDULERS=4 bash ./ex/chat_server.sh run 127.0.0.1
```

Remember to set more than 2 FFI schedulers, as Std::Posix::Network module is
blocking and does not time out.

In the second terminal, run a client:

```
$ bash ./ex/client.sh make
$ bash ./ex/client.sh run 127.0.0.1
```

You should be able to send a message from the client, and the server should
display it on standard output.
