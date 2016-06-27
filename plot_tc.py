"""
  Usage:
    plot_tc.py <input>
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from docopt import docopt

args = docopt(__doc__)
print(args)

cell_width = pd.read_csv(args["<input>"])["cell_width"].values
outfile = args["<input>"].replace(".csv", ".png")

fig, ax = plt.subplots(3)

plt.suptitle("Overview about: {}".format(args["<input>"]))

a = ax[0]
a.plot(cell_width, '.')
a.set_xlabel("DRS4 cells")
a.set_ylabel("individual cell delay [ns]")
a.set_xlim(0, 1024)
a.set_xticks(np.linspace(0, 1024, 8+1))
a.grid()

a = ax[1]
a.plot((cell_width - cell_width.mean()).cumsum(), '.:')
a.set_ylabel("cumulative cell delay deviation [ns]")
a.set_xlabel("DRS4 cells")
a.set_xlim(0, 1024)
a.set_xticks(np.linspace(0, 1024, 8+1))
a.grid()

a = ax[2]
a.hist(cell_width, bins=200, histtype="step", 
	label="$\mu$:{0:.1f} $\sigma$:{1:.1f}".format(cell_width.mean(), cell_width.std())
)
a.set_xlabel("individual cell delay [ns]")
a.grid()
a.legend()
plt.savefig(outfile)