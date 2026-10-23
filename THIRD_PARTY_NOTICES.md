# Third-party materials

- `vendor/verl/` contains unmodified verl v0.9.1 at commit `1876b06d0a3e4e71e06230be10af14492ca8a75b`. It retains the upstream Apache License 2.0, copyright headers and notices. See `vendor/verl/LICENSE` and `vendor/VERL_VERSION.json`.
- `docs/assets/paper.pdf` is the supplied manuscript. Paper figures and case images in `docs/assets/` and `data/paper_examples/images/` are derived from it. Their rights remain with the respective rights holders.
- EmbodiedBench, AI2-THOR, Qwen model weights and their full datasets are not redistributed here. Setup and usage are subject to their upstream terms and licenses.
- Transformers, PEFT, Ray and the other packages are installed from their upstream distributions.
- The continuous simulation recordings in `docs/assets/simulations/` were rendered with RoboCasa365, robosuite and LIBERO-PRO. The BDDL task variants were generated with LIBERO-PRO's official perturbators. Source revisions and asset provenance are recorded in `scripts/simulations/sources.json` and `assets.json`; upstream simulator source, models and asset archives are not redistributed. Their respective upstream licenses and asset terms remain applicable.

No repository-wide open-source license has yet been selected for the newly added implementation. Public repository visibility does not replace a license grant. Third-party licenses remain in force for their respective material.
