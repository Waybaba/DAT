# DAT: Distribution Aware Tuning
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
bash run_dat.sh
# Logs of DAT model on Cityscapes_to_ACDC and SHIFT datasets can be found in ./results_logs/
```

## Run @waybaba

## License
Non-commercial. Code is heavily based on Segformer. Please also check Segformer's LICENSE.

