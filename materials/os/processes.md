# Chapter 3: Processes

<!-- page: 6 -->

A process is a program in execution with its own address space.
The ready queue holds processes that are waiting for the CPU.
A context switch saves one process state and restores another.
Round robin scheduling gives each ready process a time slice, then moves it to the tail of the queue.
A deadlock needs mutual exclusion, hold and wait, no preemption, and circular wait together.
The fork system call creates a child process.
