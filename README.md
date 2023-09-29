# Cityscapes to ACDC
## environment setup
```
conda env create -f environment_segformer.yaml
pip install -e . --user
conda activate segformer
```
## Run
```
bash run_base.sh
bash run_tent.sh
bash run_cotta.sh
# Example rerun logs are included in ./example_logs/base.log, tent.log, and cotta.log.
```

## License
Non-commercial. Code is heavily based on Segformer. Please also check Segformer's LICENSE.

