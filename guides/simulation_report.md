# Continuous simulation demonstrations

The project homepage presents all 50 independently recorded episodes: 20 LIBERO-PRO and 30 RoboCasa365. Six use a GPT proxy and 44 use a scripted feedback controller. All use simulator-state localization with an analytical controller. They are interface demonstrations, not trained RynnBrain or frozen-VLA benchmark measurements.

Official task completion is 9/20 for LIBERO-PRO and 0/30 for RoboCasa365. Incomplete episodes remain visible. Proxy Judge fields describe the historical proxy judgments; they can be mistaken or refer to a local action and do not override the official task outcome.

All videos play continuous simulator recordings at 1× speed. Each poster is extracted from that video's first decoded frame. Execution-record buttons show English records and seek within the corresponding video using its recorded control frequency. Task definitions, seeds, step boundaries and official outcomes are preserved.

The original source records remain in `docs/assets/simulations/`. English presentation copies are in `docs/assets/simulations/records-en/`, with unchanged numeric fields and translated proxy reasoning. The original action/log archive remains available in the repository for provenance.

See [simulation scripts](../scripts/simulations/) for the recording and gallery tools. See [benchmark instructions](../README.md) for EmbodiedDiag-Bench evaluation; demonstration outcomes and manuscript benchmark scores must be reported separately.
