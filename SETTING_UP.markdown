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

Then compile Viua VM:

```
$ cd ~/viuact-workspace/viuavm
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
