#!/bin/bash

echo "inside $0"

RET=0

if [ "$LINT" == true ]; then
    echo "Linting all files with limited rules"
    flake8 statsmodels
    if [ $? -ne "0" ]; then
        echo "Changed files failed linting using the required set of rules."
        echo "Additions and changes must conform to Python code style rules."
        RET=1
    fi

    # Run with --isolated to ignore config files, the files included here
    # pass _all_ flake8 checks
    echo "Linting known clean files with strict rules"
    flake8 --isolated \
        statsmodels/resampling/ \
        statsmodels/interface/ \
        statsmodels/compat/ \
        statsmodels/datasets/tests/ \
        statsmodels/discrete/tests/results/ \
        statsmodels/duration/__init__.py \
        statsmodels/formula/ \
        statsmodels/gam/ \
        statsmodels/genmod/tests/results/ \
        statsmodels/graphics/tsaplots.py \
        statsmodels/emplike/tests/ \
        statsmodels/examples/tests/ \
        statsmodels/iolib/smpickle.py \
        statsmodels/iolib/tests/test_pickle.py \
        statsmodels/multivariate/pca.py \
        statsmodels/regression/dimred.py \
        statsmodels/regression/mixed_linear_model.py \
        statsmodels/regression/process_regression.py \
        statsmodels/regression/recursive_ls.py \
        statsmodels/regression/tests/test_dimred.py \
        statsmodels/regression/tests/test_lme.py \
        statsmodels/regression/tests/test_processreg.py \
        statsmodels/regression/tests/test_quantile_regression.py \
        statsmodels/regression/tests/results/ \
        statsmodels/robust/tests/ \
        statsmodels/sandbox/distributions/try_pot.py \
        statsmodels/sandbox/panel/correlation_structures.py \
        statsmodels/stats/__init__.py \
        statsmodels/stats/_knockoff.py \
        statsmodels/stats/base.py \
        statsmodels/stats/correlation_tools.py \
        statsmodels/stats/knockoff_regeffects.py \
        statsmodels/stats/moment_helpers.py \
        statsmodels/stats/multicomp.py \
        statsmodels/stats/regularized_covariance.py \
        statsmodels/stats/stattools.py \
        statsmodels/stats/tests/test_correlation.py \
        statsmodels/stats/tests/test_descriptivestats.py \
        statsmodels/stats/tests/test_knockoff.py \
        statsmodels/stats/tests/test_lilliefors.py \
        statsmodels/stats/tests/test_moment_helpers.py \
        statsmodels/stats/tests/test_qsturng.py \
        statsmodels/stats/tests/test_regularized_covariance.py \
        statsmodels/stats/tests/results/ \
        statsmodels/tools/linalg.py \
        statsmodels/tools/web.py \
        statsmodels/tools/tests/test_linalg.py \
        statsmodels/tools/decorators.py \
        statsmodels/tools/tests/test_decorators.py \
        statsmodels/tsa/base/tests/test_datetools.py \
        statsmodels/tsa/filters/tests/ \
        statsmodels/tsa/innovations/ \
        statsmodels/tsa/kalmanf/ \
        statsmodels/tsa/regime_switching/ \
        statsmodels/tsa/vector_ar/dynamic.py \
        statsmodels/tsa/statespace/tests/results/results_var_R.py \
        statsmodels/tsa/statespace/tests/test_var.py \
        statsmodels/conftest.py \
        statsmodels/tools/sm_exceptions.py \
        examples/ \
        tools/ \
        setup.py
    if [ $? -ne "0" ]; then
        echo "Previously passing files failed linting."
        RET=1
    fi

    # Tests any new python files
    if [ -f $(git rev-parse --git-dir)/shallow ]; then
        # Unshallow only when required, i.e., on CI
        echo "Repository is shallow"
        git fetch --unshallow --quiet
    fi
    git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"
    git fetch origin --quiet
    NEW_FILES=$(git diff origin/master --name-status -u -- "*.py" | grep ^A | cut -c 3- | paste -sd " " -)
    if [ -n "$NEW_FILES" ]; then
        echo "Linting newly added files with strict rules"
        echo "New files: $NEW_FILES"
        flake8 --isolated $(eval echo $NEW_FILES)
        if [ $? -ne "0" ]; then
            echo "New files failed linting."
            RET=1
        fi
    else
        echo "No new files to lint"
    fi
fi

exit "$RET"
