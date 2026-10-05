# v3 reference (2026-10-04): Basalt basalt_ref1 config files (copied here unchanged) plus the lamaria-slam
# patch options, set as environment variables for basalt_vio (see docs/patches/basalt-0f3b2b5.patch):
export BASALT_OUTLIER_PX=3        # post-solve reprojection filter (upstream never calls it)
export BASALT_OUTLIER_LM_RULE=1   # remove an observation only if its landmark is otherwise well fitted (median < 1.5 px)
export BASALT_DETERMINISTIC=1     # deterministic TBB reductions (bit-identical runs; default on in the patch)
# run: BASALT_VIO=<frozen binary> scripts/run_basalt_robust.sh configs/basalt_v3_ref data/training/<seq> <out>
# build note (X10): compile Basalt with -ffp-contract=off (build/dev is configured so) for results that repeat
# bit for bit across builds; the deterministic reductions above handle the thread order.
