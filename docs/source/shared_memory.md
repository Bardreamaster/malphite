# SharedMemory

{class}`SharedMemory <malphite.shared_memory.SharedMemory>` is a drop-in replacement for the standard Python `multiprocessing.shared_memory.SharedMemory` class. It provides the 'track' option for python<3.13, which allows you to control whether automatic cleanup of the shared memory object is enabled or not. For python>=3.13, it is the `multiprocessing.shared_memory.SharedMemory` class itself.

For more information about the `track` option, see [this issue](https://github.com/python/cpython/issues/82300).
