# encoding: utf-8
"""colors.py - select how to color the atoms in the GUI."""


import gtk
from ase.gui.widgets import pack, cancel_apply_ok, oops, help
import ase
from ase.data.colors import jmol_colors
import numpy as np
import colorsys

named_colors = ('green', 'yellow', 'blue', 'red', 'orange', 'cyan',
                'magenta', 'black', 'white', 'grey', 'violet', 'brown',
                'navy')

class ColorWindow(gtk.Window):
    "A window for selecting how to color the atoms."
    def __init__(self, gui):
        gtk.Window.__init__(self)
        self.gui = gui
        self.set_title("Colors")
        vbox = gtk.VBox()
        self.add(vbox)
        vbox.show()
        # The main layout consists of two columns, the leftmost split in an upper and lower part.
        self.maintable = gtk.Table(2,2)
        pack(vbox, self.maintable)
        self.methodbox = gtk.VBox()
        self.methodbox.show()
        self.maintable.attach(self.methodbox, 0, 1, 0, 1)
        self.scalebox = gtk.VBox()
        self.scalebox.show()
        self.maintable.attach(self.scalebox, 0, 1, 1, 2)
        self.colorbox = gtk.Frame()
        self.colorbox.show()
        self.maintable.attach(self.colorbox, 1, 2, 0, 2, gtk.EXPAND)
        # Upper left: Choose how the atoms are colored.
        lbl = gtk.Label("Choose how the atoms are colored:")
        pack(self.methodbox, [lbl])
        self.radio_jmol = gtk.RadioButton(None, 'By atomic number, default "jmol" colors')
        self.radio_atno = gtk.RadioButton(self.radio_jmol,
                                          'By atomic number, user specified')
        self.radio_tag = gtk.RadioButton(self.radio_jmol, 'By tag')
        self.radio_force = gtk.RadioButton(self.radio_jmol, 'By force')
        self.radio_manual = gtk.RadioButton(self.radio_jmol, 'Manually specified')
        self.radio_same = gtk.RadioButton(self.radio_jmol, 'All the same color')
        #for radio in (self.radio_jmol, self.radio_atno, self.radio_tag,
        #              self.radio_force, self.radio_manual, self.radio_same):
        for radio in (self.radio_jmol, self.radio_atno, self.radio_tag):
            pack(self.methodbox, [radio])
            radio.connect('toggled', self.method_radio_changed)
        # Lower left: Create a color scale
        pack(self.scalebox, gtk.Label(""))
        lbl = gtk.Label('Create a color scale:')
        pack(self.scalebox, [lbl])
        color_scales = (
            'Black - white',
            'Black - red - yellow - white',
            'Hue',
            'Named colors'
            )
        self.scaletype = gtk.combo_box_new_text()
        for s in color_scales:
            self.scaletype.append_text(s)
        self.createscale = gtk.Button("Create")
        pack(self.scalebox, [self.scaletype, self.createscale])
        self.createscale.connect('clicked', self.create_color_scale)
        # The actually colors are specified in a box possibly with scrollbars
        self.colorwin = gtk.ScrolledWindow()
        self.colorwin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.colorwin.show()
        self.colorbox.add(self.colorwin)
        self.colorwin.add_with_viewport(gtk.VBox()) # Dummy contents
        buts = cancel_apply_ok(cancel=lambda widget: self.destroy(),
                               apply=self.apply,
                               ok=self.ok)
        pack(vbox, [buts], end=True, bottom=True)
        # Make the initial setup of the colors
        self.color_errors = {}
        self.init_colors_from_gui()
        self.show()
        gui.register_vulnerable(self)

    def notify_atoms_changed(self):
        "Called by gui object when the atoms have changed."
        self.destroy()
  
    def init_colors_from_gui(self):
        cm = self.gui.colormode
        # Disallow methods if corresponding data is not available
        if self.gui.images.T is np.nan:
            self.radio_tag.set_sensitive(False)
            if self.radio_tag.get_active() or cm == 'tag':
                self.radio_jmol.set_active(True)
                return
        else:
            self.radio_tag.set_sensitive(True)
        if self.gui.images.F is np.nan:
            self.radio_force.set_sensitive(False)
            if self.radio_force.get_active() or cm == 'force':
                self.radio_jmol.set_active(True)
                return
        else:
            self.radio_tag.set_sensitive(True)
        # Now check what the current color mode is
        if cm == 'jmol':
            self.radio_jmol.set_active(True)
            self.set_jmol_colors()
        elif cm == 'Z':
            self.radio_atno.set_active(True)
        elif cm == 'tag':
            self.radio_tag.set_active(True)
        elif cm == 'force':
            self.radio_force.set_active(True)
        elif cm == 'manual':
            self.radio_manual.set_active(True)
        elif cm == 'same':
            self.radio_same.set_active(True)
            
    def method_radio_changed(self, widget=None):
        "Called when a radio button is changed."
        if not widget.get_active():
            return  # Ignore events when a button is turned off.
        if widget is self.radio_jmol:
            self.set_jmol_colors()
        elif widget is self.radio_atno:
            self.set_atno_colors()
        elif widget is self.radio_tag:
            self.set_tag_colors()
        # Ignore the rest for now!
            
    def make_jmol_colors(self):
        "Set the colors to the default jmol colors"
        self.colordata_z = []
        hasfound = {}
        for z in self.gui.images.Z:
            if z not in hasfound:
                hasfound[z] = True
                self.colordata_z.append([z, jmol_colors[z]])

    def set_jmol_colors(self):
        "We use the immutable jmol colors."
        self.make_jmol_colors()
        self.set_atno_colors()
        for entry in self.color_entries:
            entry.set_sensitive(False)
        self.colormode = 'jmol'
        
    def set_atno_colors(self):
        "We use user-specified per-element colors."
        if not hasattr(self, 'colordata_z'):
            # No initial colors.  Use jmol colors
            self.make_jmol_colors()
        self.actual_colordata = self.colordata_z
        self.color_labels = ["%i (%s):" % (z, ase.data.chemical_symbols[z])
                             for z, col in self.colordata_z]
        self.make_colorwin()
        self.colormode = "atno"

    def set_tag_colors(self):
        "We use per-tag colors."
        # Find which tags are in use
        tags = self.gui.images.T
        existingtags = []
        for t in range(tags.min(), tags.max()+1):
            if t in tags:
                existingtags.append(t)
        if not hasattr(self, 'colordata_tags') or len(self.colordata_tags) != len(existingtags):
            colors = self.get_named_colors(len(existingtags))
            self.colordata_tags = [[x, y] for x, y in
                                   zip(existingtags, colors)]
        self.actual_colordata = self.colordata_tags
        self.color_labels = [str(x)+':' for x, y in self.colordata_tags]
        print self.color_labels
        print self.actual_colordata
        self.make_colorwin()
        self.colormode = 'tags'

    def make_colorwin(self):
        """Make the list of editable color entries.

        Uses self.actual_colordata and self.color_labels.  Produces self.color_entries.
        """
        assert len(self.actual_colordata) == len(self.color_labels)
        self.color_entries = []
        old = self.colorwin.get_child()
        self.colorwin.remove(old)
        del old
        table = gtk.Table(len(self.actual_colordata)+1, 4)
        self.colorwin.add_with_viewport(table)
        table.show()
        self.color_display = []
        for i in range(len(self.actual_colordata)):
            lbl = gtk.Label(self.color_labels[i])
            entry = gtk.Entry(max=20)
            val = self.actual_colordata[i][1]
            error = False
            if not isinstance(val, str):
                assert len(val) == 3
                intval = tuple(np.round(65535*np.array(val)).astype(int))
                val = "%.3f, %.3f, %.3f" % tuple(val)
                clr = gtk.gdk.Color(*intval)
            else:
                try:
                    clr = gtk.gdk.color_parse(val)
                except ValueError:
                    error = True
            entry.set_text(val)
            blob = gtk.EventBox()
            space = gtk.Label
            space = gtk.Label("    ")
            space.show()
            blob.add(space)
            if error:
                space.set_text("ERROR")
            else:
                blob.modify_bg(gtk.STATE_NORMAL, clr)
            table.attach(lbl, 0, 1, i, i+1, yoptions=0)
            table.attach(entry, 1, 2, i, i+1, yoptions=0)
            table.attach(blob, 2, 3, i, i+1, yoptions=0)
            lbl.show()
            entry.show()
            blob.show()
            entry.connect('activate', self.entry_changed, i)
            self.color_display.append(blob)
            self.color_entries.append(entry)
            
    def entry_changed(self, widget, index):
        """The user has changed a color."""
        txt = widget.get_text()
        txtfields = txt.split(',')
        if len(txtfields) == 3:
            self.actual_colordata[index][1] = [float(x) for x in txtfields]
            val = tuple([int(65535*float(x)) for x in txtfields])
            clr = gtk.gdk.Color(*val)
        else:
            self.actual_colordata[index][1] = txt
            try:
                clr = gtk.gdk.color_parse(txt)
            except ValueError:
                # Cannot parse the color
                displ = self.color_display[index]
                displ.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('white'))
                displ.get_child().set_text("ERR")
                self.color_errors[index] = (self.color_labels[index], txt)
                return
        self.color_display[index].get_child().set_text("    ") # Clear error message
        self.color_errors.pop(index, None)
        self.color_display[index].modify_bg(gtk.STATE_NORMAL, clr)
        
    def create_color_scale(self, *args):
        if self.radio_jmol.get_active():
            self.radio_atno.set_active(1)
        s = self.scaletype.get_active()
        n = len(self.color_entries)
        if s == 0:
            # Black - White
            scale = self.get_color_scale([[0, [0,0,0]],
                                          [1, [1,1,1]]], n)
        elif s == 1:
            # Black - Red - Yellow - White (STM colors)
            scale = self.get_color_scale([[0, [0,0,0]],
                                          [0.33, [1,0,0]],
                                          [0.67, [1,1,0]],
                                          [1, [1,1,1]]], n)
        elif s == 2:
            # Hues
            hues = np.linspace(0.0, 1.0, n, endpoint=False)
            scale = ["%.3f, %.3f, %.3f" % colorsys.hls_to_rgb(h, 0.5, 1)
                     for h in hues]
        elif s == 3:
            # Named colors
            scale = self.get_named_colors(n)
        print scale
        for i in range(n):
            self.color_entries[i].set_text(scale[i])
            self.color_entries[i].activate()

    def get_color_scale(self, fixpoints, n):
        "Create a homogeneous color scale."
        x = np.array([a[0] for a in fixpoints], float)
        y = np.array([a[1] for a in fixpoints], float)
        assert y.shape[1] == 3
        res = []
        for a in np.linspace(0.0, 1.0, n, endpoint=True):
            n = x.searchsorted(a)
            if n == 0:
                v = y[0]  # Before the start
            elif n == len(x):
                v = x[-1] # After the end
            else:
                x0 = x[n-1]
                x1 = x[n]
                y0 = y[n-1]
                y1 = y[n]
                v = y0 + (y1 - y0) / (x1 - x0) * (a - x0)
            res.append("%.3f, %.3f, %.3f" % tuple(v))
        return res

    def get_named_colors(self, n):
        if n <= len(named_colors):
            return named_colors[:n]
        else:
            return named_colors + ('black',) * (n - len(named_colors))
        
    def apply(self, *args):
        #if self.colormode in ['atno', 'jmol', 'tags']:
        # Color atoms according to an integer value number
        if self.color_errors:
            oops("Incorrect color specification",
                 "%s: %s" % self.color_errors.values()[0])
            return False
        maxval = max([x for x, y in self.actual_colordata])
        self.gui.colors = [None] * (maxval + 1)
        new = self.gui.drawing_area.window.new_gc
        alloc = self.gui.colormap.alloc_color
        for z, val in self.actual_colordata:
            if isinstance(val, str):
                self.gui.colors[z] = new(alloc(val))
            else:
                clr = tuple([int(65535*x) for x in val])
                assert len(clr) == 3
                self.gui.colors[z] = new(alloc(*clr))
        self.gui.colormode = self.colormode
        self.gui.draw()
        return True

    def cancel(self, *args):
        self.destroy()

    def ok(self, *args):
        if self.apply():
            self.destroy()
        
