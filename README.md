# Lambda-trim Artifact

λ-trim is a debloater for Python applications. Given a Python function and a set of inputs to this function λ-trim automatically removes all redundant modules, functions and classes from the modules that the application imports.

This repository contains instructions and code to reproduce figures and results in the ASPLOS'25 paper *𝝀-trim: Optimizing Function Initialization in Serverless Applications
With Cost-driven Debloating*. The source code of λ-trim is at this [GitHub repository](https://github.com/eniac/lambda-trim) and is available at [PyPI](https://pypi.org/project/ltrim/).

## Installation and Dependencies

1. Initialize submodules
```shell
git submodule init
git submodule update --recursive --remote
```
This will initialize submodule `lambda-bench`, a public GitHub repositories where we get example serverless applications for experiments.

2. Install Python3.10, Docker, and AWS CLI. Create a virtual environment

```shell
scripts/setup.sh
python3.10 -m venv ltrim-venv
source ltrim-venv/bin/activate
```

3. Install `ltrim` and other required packages:

```shell
cd lambda-trim
pip install .
cd ..
pip install -r requirements.txt
```

4. Configure AWS CLI
```shell
aws configure
```

### Simple Example
Debloat a small application, jsym, with a small k (number of modules to debloat).
```shell
python main.py jsym -k 1
```

## Reproduce experiments

### Debloating (Figure 8)

#### Running Debloating Experiments
1. Create baseline Lambda functions by running
   ```shell
   python experiments/debloating.py --action create-baseline
   ```
   If disk space is not enough to store all Docker images, use
   ```shell
   python experiments/debloating.py --action create-baseline --cleanup
   ```
   instead to delete all existing Docker images before each build.
2. Run baseline functions
   ```shell
   python experiments/debloating.py --action run-baseline
   ```
   Results will be stored in `experiments/debloat/results/baseline`.
3. Created debloated Lambda functions.
   First, copy your AWS credentials to the corresponding fields (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY) in [experiments/debloat.py](./experiments/debloat.py). This is required to debloat applications that uses AWS services (i.e. boto3).

   Then, run
   ```shell
   python experiments/debloating.py --action create-debloat
   ```
   add `--cleanup` if not enough disk space.

   λ-trim runs in this step. It may take from 30 minutes (jsym) to 8 hours (huggingface) to debloat an application.
4. Run debloated functions
   ```shell
   python experiments/debloating.py --action run-debloat
   ```
   Results will be stored in `experiments/debloat/results/debloated`.


#### Generating Figures
Use [experiments/debloat/fig8.ipynb](./experiments/debloat/fig8.ipynb) to generate Figure 8. We provide data used in paper in `experiments/debloat/paper_results`.

### Ranking (Figure 9)

To run the experiments for the various scoring methods (memory, time, combined, random), run the following:

```shell
./experiments/ablation/run_all.sh
```

If you want to run a specific application `appname` for the various scoring methods, you can run:

```shell
./experiments/ablation/run_scoring.sh <appname>
```

Use [plot_scoring.ipynb](./experiments/ablation/plot_scoring.ipynb) to generate Figure 9.
This step assumes that you have run the debloating experiment (Figure 8) first.

### Varying K (Figure 10)

To run the experiments for varying K (number of modules to debloat), run the following:

```shell
./experiments/ablation/run_all.sh
```

If you want to run a specific application `appname` for varying K, you can run:

```shell
./experiments/ablation/run_k.sh <appname>
```

Use [plot_varying_k.ipynb](./experiments/ablation/plot_varying_k.ipynb) to generate Figure 10.
This step assumes that you have run the debloating experiment (Figure 8) first.

### Warm Starts (Figure 11)

#### Running Experiments
1. Warm-start experiments use the same functions created in the debloating experiment (Figure 8). This step can be **skipped** if baseline and debloated Lambda functions have been created in the debloating experiment (step 1 and step 3 in the debloating experiment). Otherwise, you need to do create them by running
```shell
python experiments/debloating.py --action create-baseline
python experiments/debloating.py --action create-debloat
```

2. Run warm-starts for baseline functions
```shell
python experiments/debloating.py --action run-baseline-warm
```
Results will be stored in `experiments/warm/results/baseline_warm`.

3. Run warm-starts for debloated functions
```shell
python experiments/debloating.py --action run-debloated-warm
```

#### Generating Figures
Use [fig11.ipynb](./experiments/warm/fig11.ipynb) to generate Figure 11. We provide data used in paper in `experiments/warm/paper_results`.



### Comparison with Checkpoint/Restore (Figure 12)

For our comparison with Checkpoint/Restore (CR) techniques (Figure 12), we built a prototype with [CRIU](https://github.com/checkpoint-restore/criu). 
The prototype spawns a CRIU server and the application connects to the server through a gRPC call to force a self dump/checkpoint.
Afterwards, we invoke the application by issuing a restore call to the CRIU server.

We are testing 4 variants:

- Original application
- Original application with CR
- Debloated application
- Debloated application with CR

To speed up the building process, we provide a base Docker image (`spyrospav/criu-debloat:latest`) that contains a minimum CRIU build.


For a single application `app`, you can reproduce the comparison by running:

```shell
./experiments/cr/run.sh app
```

Note, that this creates a Docker container for each variant.
The tests are executed automatically after build.

To build all the applications, run

```shell
./experiments/cr/run_all.sh
```

Use [analyze_cr.ipynb](./experiments/cr/analyze_cr.ipynb) to interactively produce the bar plots with the results for both a single application and the whole benchmark set after running the experiments (Figure 12).

#### Checkpoint size (Table 3 - Ckpt. Size column)

The size of the checkpoints (Table 3 - Ckpt. Size column) for both the original and the debloated application are saved in the directory `experiments/cr/output/` after running the experiment.

### Fallback (Table 4)

#### Running Experiments
1. Create undebloated Lambda functions to be used as fallback functions. This step can be skipped if the baseline functions `dna-visualization`, `lightgbm`, `spacy`, and `huggingface` have be created in step 1 of debloating experiment (Figure 8). Otherwise, create them by running
```shell
python experiments/debloating.py --action create-baseline --single-app dna-visualization
python experiments/debloating.py --action create-baseline --single-app lightgbm
python experiments/debloating.py --action create-baseline --single-app spacy
python experiments/debloating.py --action create-baseline --single-app huggingface
```

2. Run fallback experiments with
```shell
./experiments/fallback/run_fallback.sh
```
This script does the following 4 steps for each test application:

a. Replace the lambda handler function with another version which raises an exception when the event payload contains "raise_exception". This allows us to manually trigger a fallback.

b. Build and push a debloated function with fallback.

c. Recover the lambda hander function to the original version.

d. Invoke the function and collect results. There are 4 settings for each function: (1) principal function is cold, fallback function is cold; (2) cold - warm; (3) warm - cold; (4) cold - cold. Results will be stored in `experiments/fallback/results`.
 
### SnapStart Simulation (Figure 13 & 14)

Use [fig13_14.ipynb](./experiments/snapstart/fig13_14.ipynb) to run simulation experiments and produce fig 13 and 14. The simulation uses [Azure functions dataset 2019](https://github.com/Azure/AzurePublicDataset/blob/master/AzureFunctionsDataset2019.md) which will be downloaded in the notebook.
