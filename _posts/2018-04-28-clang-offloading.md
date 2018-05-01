---
layout: post
title: "Offloading Actions in Clang Driver"
date:   2018-04-28 02:01:15 +0800
categories: Cpp
comments: true
tags:
    - platform tool
---
<div class="message">
In heterogeneous computing, many programming models take use of computation offloading by transfering resource intensive computational tasks to an external platform, such as a cluster, grid or a cloud. Offloading may be necessary due to hardware limitations of a devices, such as limited computational power, storage, and energy. Here, we will make a birdview of the offloading action of CUDA and OpenMP in clang driver.
</div>
  <!-- more -->

## Clang Offloading Action

In clang, the offload action is expected to be used in four different situations:

```

a) Set a toolchain/architecture/kind for a host action:

   Host Action 1 -> OffloadAction -> Host Action 2

b) Set a toolchain/architecture/kind for a device action;

   Device Action 1 -> OffloadAction -> Device Action 2

c) Specify a device dependence to a host action;

   Device Action 1  _
                     \
     Host Action 1  ---> OffloadAction -> Host Action 2

d) Specify a host dependence to a device action.

     Host Action 1  _
                     \
   Device Action 1  ---> OffloadAction -> Device Action 2

```

As is shown above, clang offloading actions take two design properties:
- For a) and b), clang just returns the job generated for the dependence;
- For c) and d) clang overrides the current action with the host/device dependence if the current toolchain is host/device and set the offload dependences information with the jobs obtained from the device/host dependences.

## CUDA offloading

In clang driver module, the driver extensions for cuda mainly focuses on the support for CUDA by extending existing support with:
- Host and device actions;
- Selection of right toolchain per function based on `host, device, global` markups;
- Linker tool (fatbinary) is used to combine objects for different compute capability(not nvlink);
- Host action is used to embed device code into host-produced binary.

Let's have an overview of cuda's offloading. We can obtain the following action graph when compiling two source files for host and a CUDA device, namely kernel-call.cu and a.cpp:

![image](/assets/blog-img/2018_04_28_cuda_offload.png "CUDA offloading example")

As is shown from the figure above, if we are generating code for the device or we are in a backend phase, we attempt to generate a fat binary. Clang compiles each arch to `ptx and assemble to cubin`, then feed the `cubin and the ptx` into a device "link" action, which uses `cuda-fatbin` to combine these cubins into one fatbin.  The fatbin is then an input to the host action. During cuda device phase, clang creates an offloading action for backend and assembler action respectively. And an offload action is used to add a host dependence to the device linker actions.

By `clang kernel-call.cu a.cpp -ccc-print-phases`, we will get following pipelined phases behind clang compiling:

```
0: input, "kernel-call.cu", cuda, (host-cuda)
1: preprocessor, {0}, cuda-cpp-output, (host-cuda)
2: compiler, {1}, ir, (host-cuda)
3: input, "kernel-call.cu", cuda, (device-cuda, sm_20)
4: preprocessor, {3}, cuda-cpp-output, (device-cuda, sm_20)
5: compiler, {4}, ir, (device-cuda, sm_20)
6: backend, {5}, assembler, (device-cuda, sm_20)
7: assembler, {6}, object, (device-cuda, sm_20)
8: offload, "device-cuda (nvptx64-nvidia-cuda:sm_20)" {7}, object
9: offload, "device-cuda (nvptx64-nvidia-cuda:sm_20)" {6}, assembler
10: linker, {8, 9}, cuda-fatbin, (device-cuda)
11: offload, "host-cuda (x86_64-apple-darwin17.2.0)" {2}, "device-cuda (nvptx64-nvidia-cuda)" {10}, ir
12: backend, {11}, assembler, (host-cuda)
13: assembler, {12}, object, (host-cuda)
14: input, "a.cpp", c++, (host-cuda)
15: preprocessor, {14}, c++-cpp-output, (host-cuda)
16: compiler, {15}, ir, (host-cuda)
17: backend, {16}, assembler, (host-cuda)
18: assembler, {17}, object, (host-cuda)
19: linker, {13, 18}, image, (host-cuda)
20: bind-arch, "x86_64", {19}, image
```

And we can get the following bindings result by command `clang kernel-call.cu a.cpp -ccc-print-bindings`:

```
# "nvptx64-nvidia-cuda" - "clang", inputs: ["kernel-call.cu"], output: "/var/folders/sp/yzrv8j5s4dg6mc4bgzvcc1h80000gn/T/kernel-call-10d9de.s"

# "nvptx64-nvidia-cuda" - "NVPTX::Assembler", inputs: ["/var/folders/sp/yzrv8j5s4dg6mc4bgzvcc1h80000gn/T/kernel-call-10d9de.s"], output: "/var/folders/sp/yzrv8j5s4dg6mc4bgzvcc1h80000gn/T/kernel-call-6a0708.o"

# "nvptx64-nvidia-cuda" - "NVPTX::Linker", inputs: ["/var/folders/sp/yzrv8j5s4dg6mc4bgzvcc1h80000gn/T/kernel-call-6a0708.o", "/var/folders/sp/yzrv8j5s4dg6mc4bgzvcc1h80000gn/T/kernel-call-10d9de.s"], output: "/var/folders/sp/yzrv8j5s4dg6mc4bgzvcc1h80000gn/T/kernel-call-c3b1ee.fatbin"

# "x86_64-apple-darwin17.2.0" - "clang", inputs: ["kernel-call.cu", "/var/folders/sp/yzrv8j5s4dg6mc4bgzvcc1h80000gn/T/kernel-call-c3b1ee.fatbin"], output: "/var/folders/sp/yzrv8j5s4dg6mc4bgzvcc1h80000gn/T/kernel-call-a9bed9.o"

# "x86_64-apple-darwin17.2.0" - "clang", inputs: ["a.cpp"], output: "/var/folders/sp/yzrv8j5s4dg6mc4bgzvcc1h80000gn/T/a-cfaee5.o"

# "x86_64-apple-darwin17.2.0" - "darwin::Linker", inputs: ["/var/folders/sp/yzrv8j5s4dg6mc4bgzvcc1h80000gn/T/kernel-call-a9bed9.o", "/var/folders/sp/yzrv8j5s4dg6mc4bgzvcc1h80000gn/T/a-cfaee5.o"], output: "a.out"

```

## OpenMP Offloading

Compared to CUDA, OpenMP has relocation of symbols across host/device and the dependencies between host and device toolchains is possible. Therefore, OpenMP takes the following offloading strategy. Below is the action graph obtained when compiling two source files for host and an OpenMP device:

![image](/assets/blog-img/2018_04_28_openmp_offload.png "OpenMP offloading example")

As we can see, an offload action is used to add a host dependence to the device compile actions and add a device dependence to the host linking action[[1]](#ibm_offload_paper). The host depends on device action in the linking phase, when all the device images have to be embedded in the host image. Besides, when generating code for OpenMP, clang use the host compile phase output as a dependence to the device compile phase so that it can learn what declarations should be emitted.

Let's take OpenMP offloading for PPC64 and NVPTX64 for an example, the offloding graph is shown below:

![image](/assets/blog-img/2018_04_28_openmp_offload_ppc64_nvptx64.png "OpenMP offloading for ppc64 and nvptx64")

Here the LLVM IR for ppc64 target is the host bitcode file contains metadata that indicates what regions and functions should be compiled for device. And nvlink will link libomptarget-nvptx64 and the sass file dumped by ptxas. Here, Libomptarget-nvptx.bc will be precompiled with clang-cuda, and finally is the linking of various sections done by linker script which is generated by clang, and we will get a single `fat binary` for multiple devices, e.g. FPGA, DSP accelerator, GPU and etc.

To sum up, in contrast with CUDA, the generic offloading action for OpenMP contains:
- Replaces CUDA’s host and device actions, including:
  - The offloading kind (e.g. OpenMP, CUDA)
  - The toolchain used by the dependencies (e.g. nvptx, amd)
  - Device architecture (e.g. sm_60)
- Host to device dependency
  - The host builds a list of target regions to be compiled for device
- Device to host dependency
  - Bundling of object code in single binary

For the source code of CUDA and OpenMP offloading action, see here: <https://github.com/llvm-mirror/clang/blob/master/lib/Driver/Driver.cpp#L2127-L2538>

## REF
- [1] <span id="ibm_offload_paper">OpenMP offloading support, [paper](https://researcher.watson.ibm.com/researcher/files/us-zsura/17_llvmATSC2016.pdf) and [slide](https://llvm-hpc3-workshop.github.io/slides/Bertolli.pdf). </span>
- [2] Generic Offload File Bundler Tool: <http://clang-developers.42468.n3.nabble.com/RFC-OpenMP-CUDA-Generic-Offload-File-Bundler-Tool-td4050147.html> and [example](https://chromium.googlesource.com/external/github.com/llvm-mirror/clang/+/refs/heads/master/test/Driver/openmp-offload-gpu.c)
- [3] Clang Driver Internals: <https://clang.llvm.org/docs/DriverInternals.html>
- [4] Clang review: <https://reviews.llvm.org/D21852>
- [5] Calng review: <https://www.mail-archive.com/cfe-commits@lists.llvm.org/msg36757.html>
- [6] [CUDA][OpenMP] Add a generic offload action builder: <https://reviews.llvm.org/D18172> and revision: <http://llvm.org/viewvc/llvm-project?view=revision&revision=282865>
- [7] Clang Driver source code: <https://github.com/llvm-mirror/clang/tree/master/lib/Driver>


Any questions or suggestions, feel free to open an issue @[here](https://github.com/lijiansong/clang-llvm-tutorial) or e-mail me to *lijiansong@ict.ac.cn*.

