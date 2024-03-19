from pathlib import Path
import shutil
import numpy as np
import pandas as pd
from aicsshparam.shapespace import controller, shapespace
from aicsshparam.shapespace.shapemode_tools import ShapeModeCalculator


config = {
    "aggregation": {"type": ["avg"]},
    "appName": "cvapipe_analysis",
    "data": {
        "nucleus": {"alias": "NUC", "channel": "dna_segmentation", "color": "#3AADA7"}
    },
    "features": {
        "SHE": {
            "aliases": ["NUC"],
            "alignment": {"align": True, "reference": "nucleus", "unique": False},
            "lmax": 16,
            "sigma": 2,
        },
        "aliases": ["NUC"],
    },
    "parameterization": {
        "inner": "NUC",
        "number_of_interpolating_points": 32,
        "outer": "MEM",
        "parameterize": ["RAWSTR", "STR"],
    },
    "preprocessing": {
        "filtering": {"csv": "", "filter": False, "specs": {}},
        "remove_mitotics": True,
        "remove_outliers": True,
    },
    "project": {
        "local_staging": Path(__file__).parent / "all/shape_analysis/shape_space",
        "overwrite": True,
    },
    "shapespace": {
        "aliases": ["NUC"],
        "map_points": [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0],
        "number_of_shape_modes": 8,
        "plot": {
            "frame": False,
            "limits": [-150, 150, -80, 80],
            "swapxy_on_zproj": False,
        },
        "removal_pct": 0.25,
        "sorter": "NUC",
    },
    "structures": {
        "lamin": [
            "nuclear envelope",
            "#084AE7",
            "{'raw': (475,1700), 'seg': (0,30), 'avgseg': (0,60)}",
        ]
    },
}


def random_shcoeffs_dataframe(nrows=100):
    lmax = config["features"]["SHE"]["lmax"]
    shcoeffs_cols = [
        f"NUC_shcoeffs_L{L}M{m}{suffix}"
        for L in range(1, lmax+1)
        for m in range(0, L+1)
        for suffix in ["C", "S"]
        if suffix == "C" or m >= 1  # sine components are zero for m=0
    ]
    df = pd.DataFrame(
        data=np.random.normal(size=(nrows, len(shcoeffs_cols))),
        columns=shcoeffs_cols
    )
    df["NUC_shcoeffs_L0M0C"] = 5.0  # Each row is mostly spherical
    df["NUC_shape_volume"] = np.random.normal(size=nrows)
    df["NUC_position_depth"] = np.random.normal(size=nrows)
    df["structure_name"] = "lamin"
    return df


def assert_NUC_PC_columns_nonzero(df):
   for column in [
        "NUC_PC1",
        "NUC_PC2",
        "NUC_PC3",
        "NUC_PC4",
        "NUC_PC5",
        "NUC_PC6",
        "NUC_PC7",
        "NUC_PC8",
    ]:
        assert df[column].dtype == np.float64
        numzero = sum(df[column] == 0.0)
        # Since we used gaussian data the result should almost always have no zeros
        assert numzero < 3


def test_shapespace():
    # ARRANGE
    df = random_shcoeffs_dataframe(nrows=100)

    # ACT
    control = controller.Controller(config)
    space = shapespace.ShapeSpace(control)
    space.execute(df)

    # ASSERT
    assert len(space.shape_modes) >= 75  # Some outliers filtered out
    assert_NUC_PC_columns_nonzero(space.shape_modes)


def test_shapespace_transform():
    # ARRANGE
    df1 = random_shcoeffs_dataframe()
    df2 = random_shcoeffs_dataframe(nrows=100)

    # ACT
    control = controller.Controller(config)
    space = shapespace.ShapeSpace(control)
    space.execute(df1)
    result = space.pca.transform(df2[[c for c in df2.columns if "shcoeffs" in c]].values)

    # ASSERT
    assert len(result) == 100  # No outliers filtered out
    result_as_df = pd.DataFrame(result, columns=[f"NUC_PC{i}" for i in range(1, 9)])
    assert_NUC_PC_columns_nonzero(result_as_df)


def test_shape_mode_viz():
    # ARRANGE
    df = random_shcoeffs_dataframe(nrows=50)

    # ACT
    control = controller.Controller(config)
    calculator = ShapeModeCalculator(control)
    calculator.set_data(df)
    calculator.execute()

    # ASSERT
    directory = config["project"]["local_staging"]
    assert (directory / "shapemode/pca/explained_variance.png").exists()
    assert (directory / "shapemode/avgshape/combined.tif").exists()
    assert (directory / "shapemode/avgshape/NUC_PC8_z.gif").exists()

    # Clean up
    shutil.rmtree(Path(__file__).parent / "all")
