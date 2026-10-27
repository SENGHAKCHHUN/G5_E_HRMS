"""Charts (matplotlib embedded in Tk)."""
import customtkinter as ctk

from .. import theme as T

from .basics import label


def donut_chart(master, values, colors, center_text="", size=120, bg=T.SURFACE):
    """Matplotlib donut embedded in Tk; falls back to a plain label if unavailable."""
    try:
        import matplotlib
        matplotlib.use("TkAgg")
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
    except ImportError:
        return label(master, center_text, size=20, weight="bold")

    dpi = 100
    fig = Figure(figsize=(size / dpi, size / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    canvas = FigureCanvasTkAgg(fig, master=master)
    w = canvas.get_tk_widget()
    w.configure(highlightthickness=0, bd=0)

    def paint(_mode=None):
        """Draw in the current light/dark colours (matplotlib does not follow CTk's mode by itself)."""
        ax.clear()
        fig.patch.set_facecolor(T.pick(bg))
        ax.pie(values, colors=[T.pick(c) for c in colors], startangle=90, counterclock=False,
               wedgeprops={"width": 0.22, "edgecolor": T.pick(bg), "linewidth": 2})
        ax.set_aspect("equal")
        ax.text(0, 0, center_text, ha="center", va="center", fontsize=13, fontweight="bold",
                color=T.pick(T.TEXT))
        canvas.draw()
        w.configure(bg=T.pick(bg))

    paint()
    ctk.AppearanceModeTracker.add(paint, w)
    w.bind("<Destroy>", lambda _e: ctk.AppearanceModeTracker.remove(paint), add="+")
    return w
