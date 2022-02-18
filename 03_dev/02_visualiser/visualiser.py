"""
================================================================================
 * @file 	visualiser.py
 * @author 	Mitch Manning - s4532126
 * @date 	27-07-2021
 * @brief 	Visualises the data from the AWR1843 and Logitech C920.
================================================================================
"""
# Standard
import os
import sys
import time
import tkinter as tk
from math import floor, pi, ceil
import subprocess as sp
from datetime import datetime, timedelta
from collections import OrderedDict
# Non-Standard
import numpy as np                              # 'numpy'
import pandas as pd                             # 'pandas'
from sklearn.cluster import k_means             # 'sklearn'
from PIL import Image                           # 'pil'
from kneed import KneeLocator                   # 'kneed'
from scipy.spatial import distance              # 'scipy'
import matplotlib.pyplot as plt                 # 'matplotlib'
import matplotlib.dates as md
import matplotlib.ticker as ti
import matplotlib.patches as pa
# Custom
from network_client import *


# GUI Characteristics
FOV_AWR1843         = 120   # Deg.
ACTIVITY_THRESHOLD  = 0.3   # %
DIST_THRESHOLD      = 4     # m
CAR_SPACE_X         = 2.4   # m
CAR_SPACE_Y         = 5.4   # m
AVG_PT_CLD_SIZE     = 20
AWR1843_TILT        = 10    # Deg.
PLAYBACK_MODE       = 0
LIVE_MODE           = 1
MIN_TGT_SIZE        = 10
BOUNDARY_EXT        = 15    # m
PROC_ERR            = 1e-3
MEAS_ERR            = 1e-2


class Radar_Plot(object):
    """
    @brief  Handles all functionality relating to managing and displaying the 
            radar data.
    @param  None
    @return None
    """
    def __init__(self, axis, x_dist, y_dist):
        """
        @brief  Initialises the class variables and the plot.
        @param  self is the instance of the class.
        @param  axis is the instance of the axis in the figure.
        @return None
        """
        # Initialise class variables for the radar
        self.ax = axis
        self.sc_active = self.ax.scatter([], [], s=120, c='lime', alpha=1.0, 
            label='Active')
        self.sc_inactive = self.ax.scatter([], [], s=120, c='red', alpha=1.0, 
            label='Inactive')
        self.sc_pt_cld = self.ax.scatter([], [], s=25, c='black', 
            alpha=0.15)
        self.ax.add_patch(pa.Wedge(center=(0,0), r=2*y_dist, 
            theta1=(90 - FOV_AWR1843/2), theta2=(90 + FOV_AWR1843/2), 
            fc='none', ec='black', alpha=0.75))
        
        # Customise the axis plot
        self.ax.set_title('AWR1843 Data')
        self.ax.set_xlabel('x [m]')
        self.ax.set_ylabel('y [m]')
        self.ax.grid(True)
        self.ax.legend(loc=3)
        self.ax.set_xlim(-x_dist/2, x_dist/2)
        self.ax.set_ylim(0, y_dist)
        self.ax.xaxis.set_major_locator(ti.MaxNLocator(9))
        self.ax.yaxis.set_major_locator(ti.MaxNLocator(9))
        self.ax.set_xticks(np.linspace(-x_dist/2, x_dist/2, 9))
        self.ax.set_xticklabels(np.linspace(-x_dist/2, x_dist/2, 9))
        self.ax.set_yticks(np.linspace(0, y_dist, 9))
        self.ax.set_yticklabels(np.linspace(0, y_dist, 9))

    def update(self, active_pos, inactive_pos, pt_cld_pos):
        """
        @brief  Updates the axis plot for the radar.
        @param  self is the instance of the class.        
        @param  target_pos is the list of the target coordinates (x,y).
        @param  pt_cld_pos is the list of particle point coordinates (x,y).
        @return None
        """
        # Initialise arrays for targets and particle clouds (x,y)
        active_x    = np.zeros(0, dtype=float)
        active_y    = np.zeros(0, dtype=float)
        inactive_x  = np.zeros(0, dtype=float)
        inactive_y  = np.zeros(0, dtype=float)
        pt_cld_x    = np.zeros(0, dtype=float)
        pt_cld_y    = np.zeros(0, dtype=float)

        # Append data to respective lists
        for x, y in active_pos:
            active_x = np.append(active_x, [x])
            active_y = np.append(active_y, [y])

        for x, y in inactive_pos:
            inactive_x = np.append(inactive_x, [x])
            inactive_y = np.append(inactive_y, [y])

        for x, y in pt_cld_pos:
            pt_cld_x = np.append(pt_cld_x, [x])
            pt_cld_y = np.append(pt_cld_y, [y])

        # Update the scatter plots
        self.sc_active.set_offsets(np.c_[active_x, active_y])
        self.sc_inactive.set_offsets(np.c_[inactive_x, inactive_y])
        self.sc_pt_cld.set_offsets(np.c_[pt_cld_x, pt_cld_y])

class Image_Plot(object):
    """
    @brief  Handles all functionality relating to managing and displaying the 
            image data.
    @param  None
    @return None
    """
    def __init__(self, axis):
        """
        @brief  Initialises the class variables and the plot.
        @param  self is the instance of the class.
        @param  axis is the instance of the axis in the figure.
        @return None
        """
        # Initialise class variables for the image
        self.ax     = axis
        self.img    = self.ax.imshow(Image.new('RGB', (1280, 720)))

        # Customise the axis plot
        self.ax.set_title('Logitech C920 Data')
        self.ax.xaxis.set_visible(False)
        self.ax.yaxis.set_visible(False)

    def update(self, img_arr):
        """
        @brief  Updates the axis plot for the image.
        @param  self is the instance of the class.
        @param  img_arr is the new image data captured from the Logitech C920.
        @return None
        """
        # Convert image data to correct format and update plot
        image = Image.fromarray(img_arr)
        self.img.set_data(image)

class Heatmap_Plot(object):
    """
    @brief  Handles all functionality relating to managing and displaying the 
            heatmap data.
    @param  None
    @return None
    """
    def __init__(self, axis, x_dist, y_dist):
        """
        @brief  Initialises the class variables and the plot.
        @param  self is the instance of the class.
        @param  axis is the instance of the axis in the figure.
        @return None
        """
        # Initialise class variables for the heatmap
        self.ax = axis
        self.iterations = 0
        self.data = np.zeros((2*y_dist+1, 2*x_dist+1), dtype=float)
        self.hmap = np.zeros((2*y_dist+1, 2*x_dist+1), dtype=float)
        self.summary_data = np.zeros((2*y_dist+1, 2*x_dist+1), dtype=float)
        self.summary_hmap = np.zeros((2*y_dist+1, 2*x_dist+1), dtype=float)
        self.heatmap = self.ax.imshow(self.hmap, cmap='jet', aspect='auto', 
            vmin=0, vmax=1)

        # Customise the axis plot
        self.ax.set_title('Heatmap')
        self.ax.set_xlabel('x [m]')
        self.ax.set_ylabel('y [m]')
        self.ax.set_xlim(0, 2*x_dist)
        self.ax.set_ylim(0, 2*y_dist)
        self.ax.xaxis.set_major_locator(ti.MaxNLocator(9))
        self.ax.yaxis.set_major_locator(ti.MaxNLocator(9))
        self.ax.set_xticks(np.linspace(0, 2*x_dist, 9))
        self.ax.set_xticklabels(np.linspace(-x_dist/2, x_dist/2, 9))
        self.ax.set_yticks(np.linspace(0, 2*y_dist, 9))
        self.ax.set_yticklabels(np.linspace(0, y_dist, 9))

        # Customise the colour bar
        cbar = self.ax.figure.colorbar(self.heatmap, ax=self.ax)
        cbar.ax.get_yaxis().labelpad = 15
        cbar.ax.set_ylabel('Occupancy [%]', rotation=270)
        cbar.ax.get_yaxis().set_ticks(np.linspace(0, 1, 5))
        cbar.ax.get_yaxis().set_ticklabels(np.linspace(0, 100, 5))

    def update(self, targets, x_dist, y_dist):
        """
        @brief  Updates the axis plot for the heatmap.
        @param  self is the instance of the class.
        @param  targets is a list of tracked targets from the AWR1843.
        @return active_tgts, inactive_tgts are lists categorising the targets.
        """
        # Convert targtet coords to heatmap coords
        arr_tgts = []
        for x, y in targets:
            x = floor(((x_dist / 2) + x) * 2)
            y = floor(y * 2)
            arr_tgts.append((x, y))

        # Adjust heatmap data values based on target position
        for x in range(2 * x_dist):
            for y in range(2 * y_dist):
                if (x, y) in arr_tgts:
                    for neigh_x in np.linspace(-2, 2, 5, dtype=int):
                        for neigh_y in np.linspace(-2, 2, 5, dtype=int):
                            nx, ny = neigh_x + x, neigh_y + y
                            if nx in range(0, 2*x_dist) and ny in range(0, 
                                    2*y_dist):
                                val = max(abs(neigh_x), abs(neigh_y))
                                if val == 0:
                                    self.data[ny][nx] += 1
                                    self.summary_data[ny][nx] += 1
                                elif val == 1:
                                    self.data[ny][nx] += 0.75
                                else:
                                    self.data[ny][nx] += 0.5
        
        # Apply scaling factor and determine active/inactive targets
        active_tgts, inactive_tgts = [], []
        for x in range(2 * x_dist):
            for y in range(2 * y_dist):
                max_val = self.data.max() + 1
                self.hmap[y][x] = self.data[y][x] / max_val
                self.summary_hmap[y][x] = self.summary_data[y][x] / max_val
                if (x, y) in arr_tgts:
                    i = arr_tgts.index((x, y))
                    if self.hmap[y][x] > ACTIVITY_THRESHOLD:
                        inactive_tgts.append(targets[i])
                    else:
                        active_tgts.append(targets[i])

        # Update heatmap data and update iterations
        self.iterations += 1
        self.heatmap.set_data(self.hmap)

        return active_tgts, inactive_tgts

    def save_summary(self, x_dist, y_dist, filename):
        """
        @brief  Determine parking spot centers and approximates location and 
                occupancy throughout recording.
        @param  x_dist is the user specified X value.
        @param  y_dist is the user specified Y value.
        @param  filename is the user specified file name.
        @return None
        """
        # Customise the axis plot
        fig, ax = plt.subplots()
        ax.set_title('Parking Summary')
        ax.set_xlabel('x [m]')
        ax.set_ylabel('y [m]')
        ax.grid(True)
        x_lim = (CAR_SPACE_X + x_dist) / 2
        y_lim = (CAR_SPACE_Y / 2) + y_dist
        ax.set_xlim(-x_lim, x_lim)
        ax.set_ylim(0, y_lim)
        ax.xaxis.set_major_locator(ti.MaxNLocator(9))
        ax.yaxis.set_major_locator(ti.MaxNLocator(9))
        ax.set_xticks(np.linspace(-x_lim, x_lim, 9))
        ax.set_xticklabels(np.linspace(-x_lim, x_lim, 9))
        ax.set_yticks(np.linspace(0, y_lim, 9))
        ax.set_yticklabels(np.linspace(0, y_lim, 9))
        ax.xaxis.set_major_formatter(ti.FormatStrFormatter('%.2f'))
        ax.yaxis.set_major_formatter(ti.FormatStrFormatter('%.2f'))

        # Determine the hotzones
        hotzones = np.ma.MaskedArray(self.summary_hmap, self.summary_hmap < \
            ACTIVITY_THRESHOLD)
        parking_y, parking_x = hotzones.nonzero() # row, col from top left
        num_hot_pts = len(parking_y)
        
        if num_hot_pts > 0:
            # Determine approximate parking spot centers
            pts_data = {}
            for i in range(0, num_hot_pts):
                x1, y1 = parking_x[i], parking_y[i]
                not_set = True
                for (x2, y2), (num, score) in pts_data.items():
                    if distance.euclidean([x1, y1], [x2, y2]) < 3:
                        x_new = (x2 * num + x1) / (num + 1)
                        y_new = (y2 * num + y1) / (num + 1)
                        pts_data.pop((x2, y2))
                        pts_data[(x_new, y_new)] = [num + 1, score + \
                            self.summary_data[y1][x1]]
                        not_set = False
                        break
                if not_set:
                    pts_data[(x1, y1)] = [1, self.summary_data[y1][x1]]

            # Convert points to list
            hot_pts_data = OrderedDict(sorted(pts_data.items(), key=lambda \
                k:k[0]))
            hot_pts = [i for i in hot_pts_data.keys()]
            scores = [f'{round(100*s/self.iterations)}%' for _, s in \
                hot_pts_data.values()]

            # Calculate average X Value ~2.4m (5 blocks)
            x_pts = [i[0] for i in hot_pts]
            x_new = [x_pts[0]]
            for i, x in enumerate(x_pts):
                if i > 0:
                    n = round((x - x_new[0]) / 5)
                    x_new.append(x_new[0] + n*5)
            x_pts = x_new

            # Calculate average Y Value ~5.4m (11 blocks)
            y_pts = [i[1] for i in hot_pts]
            avg_y = sum(y_pts) / len(y_pts)

            # Convert to real coordinates for rectangle plotting
            hot_pts = []
            for x in x_pts:
                x = ((x - x_dist) / 2) - (CAR_SPACE_X / 2)
                y = avg_y / 2 - (CAR_SPACE_Y / 2)
                hot_pts.append((x, y))

            for i, pt in enumerate(hot_pts):            
                rect = plt.Rectangle(pt, CAR_SPACE_X, CAR_SPACE_Y, fc='none', \
                    ec='red')
                plt.gca().add_patch(rect)
                ax.text((pt[0] + (CAR_SPACE_X/2)), (pt[1] + (CAR_SPACE_Y/2)), \
                    scores[i], fontsize=15, color='red', \
                    horizontalalignment='center')

        # Save the figure as an image
        name = "outputs/CaptureSummary_"
        filename = filename.split('/')[-1][:-4]
        if filename != 'None':
            name += (filename + ".png")
        else:
            name += ("LIVE_" + datetime.now().strftime("%H-%M-%S") + ".png")
        fig.savefig(name, bbox_inches='tight')

class Occupancy_Plot(object):
    """
    @brief  Handles all functionality relating to managing and displaying the 
            occupancy data.
    @param  None
    @return None
    """
    def __init__(self, axis):
        """
        @brief  Initialises the class variables and the plot.
        @param  self is the instance of the class.
        @param  axis is the instance of the axis in the figure.
        @return None
        """
        # Initialise class variables for the occupancy graph
        self.ax             = axis
        self.time_vals      = np.zeros(0, dtype=datetime)
        self.predict_vals   = np.zeros(0, dtype=int)
        self.active_vals    = np.zeros(0, dtype=int)
        self.inactive_vals  = np.zeros(0, dtype=int)
        self.occupancy_vals = np.zeros(0, dtype=int)
        self.prediction,    = self.ax.plot([], [], color='black', linestyle=':', 
            label='Prediction')
        self.active,        = self.ax.plot([], [], color='lime', label='Active')
        self.inactive,      = self.ax.plot([], [], color='red', 
            label='Inactive')
        self.occupancy,     = self.ax.plot([], [], color='black', 
            label='Occupancy')

        # Customise the axis plot
        self.ax.set_title('Occupancy Graph')
        self.ax.set_xlabel('Time Stamp [H:M:S]')
        self.ax.set_ylabel('Occupancy')
        self.ax.grid(True)
        self.ax.legend(loc=2)
        self.ax.xaxis.set_major_formatter(md.DateFormatter('%H:%M:%S'))
        self.ax.xaxis.set_major_locator(ti.MaxNLocator(5))
        self.ax.yaxis.set_major_locator(ti.MaxNLocator(6))

    def update(self, time_val, prediction, active_num, inactive_num):
        """
        @brief  Updates the axis plot for the occupancy.
        @param  self is the instance of the class.
        @param  time_val is the latest time stamp received.
        @param  predict_val is the latest occupancy prediction.
        @param  actual_val is the latest known occupancy.
        @return None
        """
        # Update the class variables
        self.time_vals      = np.append(self.time_vals, [time_val])
        self.predict_vals   = np.append(self.predict_vals, [prediction])
        self.active_vals    = np.append(self.active_vals, [active_num])
        self.inactive_vals  = np.append(self.inactive_vals, [inactive_num])
        self.occupancy_vals = np.append(self.occupancy_vals, [active_num + 
            inactive_num])

        # Update the line graph plots
        self.prediction.set_xdata(self.time_vals)
        self.prediction.set_ydata(self.predict_vals)
        self.active.set_xdata(self.time_vals)
        self.active.set_ydata(self.active_vals)
        self.inactive.set_xdata(self.time_vals)
        self.inactive.set_ydata(self.inactive_vals)
        self.occupancy.set_xdata(self.time_vals)
        self.occupancy.set_ydata(self.occupancy_vals)

        # Calculate and update new axis limits
        x_min, x_max = min(self.time_vals), max(self.time_vals)
        y_min, y_max = min(min(self.predict_vals), min(self.active_vals), 
                       min(self.inactive_vals), min(self.occupancy_vals)), \
                       max(max(self.predict_vals), max(self.active_vals), 
                       max(self.inactive_vals), max(self.occupancy_vals))
        self.ax.set_xlim(x_min, x_max + timedelta(seconds=10))
        self.ax.set_ylim(y_min, (y_max + 1))

class Data_Visualiser(object):
    """
    @brief  Handles the figure which displays the subplots and their data.
    @param  None
    @return None
    """
    def __init__(self):
        """
        @brief  Initialises the class variables for the figure.
        @param  self is the instance of the class.
        @return None
        """
        # Initialise class variables for the figure
        self.fig, self.axes = plt.subplots(2, 2)

        # Define the figure characterisitcs
        plt.ion()
        plt.tight_layout()
        plt.get_current_fig_manager().window.state("zoomed")
        plt.get_current_fig_manager().set_window_title('ENGG4811: Visualiser')

    def get_axes(self):
        """
        @brief  Returns the axes instances.
        @param  self is the instance of the class.
        @return The axes instances.
        """
        return self.axes

    def refresh(self):
        """
        @brief  Refreshes the subplots after their data has been updated.
        @param  self is the instance of the class.
        @return None
        """
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        time.sleep(0.01)

class Data_Entry(object):
    """
    @brief  Handles all functionality relating to gathering user input for 
            environment and deployment. 
    @param  None
    @return None
    """
    def __init__(self):
        """
        @brief  Initialises the class variables for the collecting input.
        @param  self is the instance of the class.
        @return None
        """
        # Initialise class variables
        self.data_set   = False
        self.mode       = None
        self.x          = 0
        self.y          = 0
        self.height     = 0
        self.az         = 0
        self.el         = -AWR1843_TILT * (pi/180)
        self.server_ip  = None
        self.filename   = None
        self.rot_az     = None
        self.rot_el     = None
        self.tran_M     = None

        # Initialise the main window
        self.root = tk.Tk()
        self.root.title('ENGG4811: Deployment Details')
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.w, self.h = sw/4, sh/2
        self.root.geometry('+%d+%d' % ((sw-self.w)/2, (sh-self.h)/2))
        self.canvas = tk.Canvas(self.root, width=self.w, height=self.h)
        self.canvas.pack()

        # Create window heading
        self.create_heading()

        # Create data entries
        self.vals = []
        self.create_entry('X [m]:', 2, '10')
        self.create_entry('Y [m]:', 3, '10')
        self.create_entry('Height [m]:', 4, '2')
        self.vals.append(tk.StringVar())
        self.vals[3].set('None')
        self.create_dropdowns('Server IP [IPv4]:', self.vals[3], 5,\
            'None', self.get_valid_ip())
        self.vals.append(tk.StringVar())
        self.vals[4].set('None')
        self.create_dropdowns('File Name [*.pkl]:', self.vals[4], 6,\
            'None', self.get_valid_files())

        # Create Button
        self.create_button()

        # Start Main
        self.root.mainloop()

    def create_heading(self):
        """
        @brief  Creates the heading widget for the canvas.
        @param  self is the instance of the class.
        @return None
        """
        heading_label = tk.Label(self.root, text='Deployment Details')
        heading_label.config(font=('helvetica', 14))
        self.canvas.create_window(self.w/2, self.h/8, window=heading_label)

    def create_entry(self, txt, pos, init_val):
        """
        @brief  Creates an entry widget for the canvas.
        @param  self is the instance of the class.
        @param  txt is the text to describe the entry.
        @param  pos is the multiplier to assist positioning the widget.
        @param  init_val is the default value displayed in the entry box.
        @return None
        """
        label = tk.Label(self.root, text=txt, justify='center')
        label.config(font=('helvetica', 10))
        self.canvas.create_window(self.w/3, pos*self.h/8, window=label)
        entry = tk.Entry(self.root, justify='center')
        entry.insert(0, init_val)
        self.canvas.create_window(2*self.w/3, pos*self.h/8, window=entry)
        self.vals.append(entry)

    def create_dropdowns(self, txt, var, pos, default, options):
        """
        @brief  Creates an drop down widget for the canvas.
        @param  self is the instance of the class.
        @param  txt is the text to describe the entry.
        @param  var is the variable linked to the drop down menu.
        @param  pos is the multiplier to assist positioning the widget.
        @param  default is the default option in the drop down menu.
        @param  options is a list of valid selections.
        @return None
        """
        label = tk.Label(self.root, text=txt, justify='center')
        label.config(font=('helvetica', 10))
        self.canvas.create_window(self.w/3, pos*self.h/8, window=label)
        drop = tk.OptionMenu(self.root, var, default, *options)
        self.canvas.create_window(2*self.w/3, pos*self.h/8, window=drop)

    def create_button(self):
        """
        @brief  Creates the button widget for the canvas.
        @param  self is the instance of the class.
        @return None
        """
        button = tk.Button(text='Launch!', command=self.set_config, 
            bg='brown', fg='white', font=('helvetica', 10, 'bold'))
        self.canvas.create_window(self.w/2, 7*self.h/8, window=button)

    def set_config(self):
        """
        @brief  Functionality for verifying the input data.
        @param  self is the instance of the class.
        @return None
        """
        try:
            self.x = int(self.vals[0].get())
            if self.x <= 0:
                raise ValueError
        except ValueError:
            sys.exit('[GUI] X must be a positive whole number.')

        try:
            self.y = int(self.vals[1].get())
            if self.y <= 0:
                raise ValueError
        except ValueError:
            sys.exit('[GUI] Y must be a positive whole number.')
            
        try:
            self.height = float(self.vals[2].get())
            if self.height <= 0:
                raise ValueError
        except ValueError:
            sys.exit('[GUI] Height must be a positive number.')

        try:
            self.server_ip = str(self.vals[3].get())
            if self.server_ip != 'None':
                test_sock = s.socket(s.AF_INET, s.SOCK_STREAM)
                test_sock.connect((self.server_ip, PORT))
                test_sock.close()
                self.mode = LIVE_MODE
        except (ValueError, ConnectionRefusedError):
            sys.exit('[GUI] Server IP must match the host\'s IPv4 format.')

        try:
            self.filename = str(self.vals[4].get())
            if self.filename != 'None':
                self.filename = 'raw_data/' + self.filename
                test_file = open(self.filename, 'rb')
                test_file.close()
                if self.mode == LIVE_MODE:
                    print('[GUI] Server IP and File Name given -'\
                        ' Default to Server IP')
                else:
                    self.mode = PLAYBACK_MODE
        except (ValueError, FileNotFoundError):
            sys.exit('[GUI] File name must be a valid \'.pkl\' file type.')

        if self.mode == None:
            sys.exit('[GUI] A valid IPv4 address or file name must be '\
                'selected.')
       
        self.get_matrices()
        self.data_set = True
        self.root.destroy()

    def get_matrices(self):
        """
        @brief  Calculates the transformation matrices for interpreting radar 
                data.
        @param  self is the instance of the class.
        @return None
        """
        self.rot_az = np.matrix([[np.cos(self.az), -np.sin(self.az), 0], 
                                 [np.sin(self.az), np.cos(self.az), 0], 
                                 [0, 0, 1]])
        self.rot_el = np.matrix([[1, 0, 0], 
                                 [0, np.cos(self.el), -np.sin(self.el)], 
                                 [0, np.sin(self.el), np.cos(self.el)]])
        self.tran_M = self.rot_az * self.rot_el

    def get_valid_ip(self):
        """
        @brief  Obtains valid IPv4 addresses on the local network.
        @param  self is the instance of the class.
        @return A list of valid dynamic IPv4 addresses on the local network.
        """
        # Command: arp -a
        arp_req = sp.Popen(['arp', '-a'], stdin=sp.PIPE, stdout=sp.PIPE,\
            stderr=sp.STDOUT)
        out = arp_req.communicate()[0].decode('ascii').rsplit()

        # Retrieve valid IPs
        valid_ips = [out[1]]
        for i, item in enumerate(out):
            if item == 'dynamic':
                valid_ips.append(out[i-2])
        
        return sorted(valid_ips)

    def get_valid_files(self):
        """
        @brief  Obtains valid data files in the data folder.
        @param  self is the instance of the class.
        @return A list of valid data files.
        """
        # Get list of files in data directory
        files = os.listdir('raw_data/')

        # Determine valid files
        valid_files = []
        for f in files:
            if f[-4:] == '.pkl':
                valid_files.append(f)
        
        return valid_files

class KalmanFilter(object):
    """
    @brief  Kalman filter used to measure and predict target positions.
    @param  None
    @return None
    """
    def __init__(self, pos):
        """
        @brief  Initialises the kalman filter for a new target and sets initial 
                estimate to be raw measured value.
        @param  pos is the initial measured position of the target.
        @return None
        """
        self.ndim = len(np.array(pos))
        self.A = np.eye(self.ndim)
        self.H = np.eye(self.ndim)
        self.x_hat =  np.array(pos)
        self.cov = np.eye(2)
        self.Q_k = np.eye(self.ndim) * PROC_ERR
        self.R = np.eye(len(self.H)) * MEAS_ERR
        self.x_hat_est = self.x_hat

    def __repr__(self):
        """
        @brief  Overwrites the print functionality to display the estimate 
                position.
        @param  None
        @return The print statement.
        """
        return '({0}, {1})'.format(self.x_hat[0], self.x_hat[1])

    def predict(self):
        """
        @brief  Predicts the next position given the current state.
        @param  None
        @return None
        """
        self.x_hat_est = np.dot(self.A, self.x_hat)
        self.cov_est = np.dot(self.A, np.dot(self.cov, np.transpose(self.A))) +\
            self.Q_k

    def update(self, pos):
        """
        @breif  Updates the estimate position using the newly recorded
                measurement.
        @param  pos is the new measurement.
        @return None
        """
        self.predict()
        self.error_x = np.array(pos) - np.dot(self.H,self.x_hat_est)
        self.error_cov = np.dot(self.H, np.dot(self.cov_est, \
            np.transpose(self.H))) + self.R
        self.K = np.dot(np.dot(self.cov_est, np.transpose(self.H)), \
            np.linalg.inv(self.error_cov))
        self.x_hat = self.x_hat_est + np.dot(self.K, self.error_x)
        if self.ndim > 1:
            self.cov = np.dot((np.eye(self.ndim) - np.dot(self.K,self.H)), \
                self.cov_est)
        else:
            self.cov = (1 - self.K) * self.cov_est

class Network_Pkt(object):
    """
    @brief  Handles all functionality relating to filtering the received network
            packet. 
    @param  None
    @return None
    """
    def __init__(self, net_pkt, inputs, prev_tgts):
        """
        @brief  Interprets and initialises the class variables for the GUI to 
                use.
        @param  self is the instance of the class.
        @param  net_pkt is the received network packet from the sensor system.
        @param  inputs is the class representing the user defined inputs.
        @param  prev_tgts is the previous packets identified targets.
        @return None
        """
        self.time_val   = net_pkt['time']
        self.img_arr    = net_pkt['img_data']
        self.prediction = net_pkt['img_objs']
        self.lim_x      = int(inputs.x/2) + BOUNDARY_EXT
        self.lim_y      = int(inputs.y)
        self.rot_el     = inputs.rot_el
        self.tran_M     = inputs.tran_M
        self.particles  = self.get_pc_pos(net_pkt)
        self.tgt_state  = self.get_tgt_pos(prev_tgts, self.particles)
        self.targets    = [self.tgt_state[i].x_hat for i in self.tgt_state]

    def get_pc_pos(self, net_pkt):
        """
        @brief  Obtains the positions of the particle clouds points.
        @param  self is the instance of the class.
        @param  net_pkt is the received network packet from the sensor system.
        @return The coordinates of the particle cloud points.
        """
        coords = []
        # Particle data received
        if 'pc_sph_data' in net_pkt:
            # Interpret data
            ranges      = net_pkt['pc_sph_data']['ranges']
            azimuth     = net_pkt['pc_sph_data']['azimuth']
            elevation   = net_pkt['pc_sph_data']['elevation']
            
            # Apply math to find true coordinates
            x = ranges * np.cos(elevation) * np.sin(azimuth)
            y = ranges * np.cos(elevation) * np.cos(azimuth)
            z = ranges * np.sin(elevation)
            pt_cld = self.tran_M * np.matrix([x, y, z])

            # If a valid packet coordinate then add to list
            for i in range(len(ranges)):
                pt_x, pt_y = pt_cld[0, i], pt_cld[1, i]
                if (-self.lim_x <= pt_x <= self.lim_x) and (0 <= pt_y <= \
                        self.lim_y):
                    coords.append((pt_x, pt_y))
        
        return coords
    
    def get_tgt_pos(self, prev_tgts, pt_cld):
        """
        @brief  Obtains the positions of the targets.
        @param  self is the instance of the class.
        @param  prev_tgts is the previous packets identified targets.
        @param  pt_cld is the coordinates of the particle cloud points.
        @return The target coordinates in a dictionary with ID as the key.
        """
        # Assign current target state
        tgt_state = prev_tgts
        
        # If particles are present then apply filtering
        if pt_cld:
            
            # K-Means Clustering Algorithm
            data_pts = {'x': [], 'y': []}
            for x, y in pt_cld:
                data_pts['x'].append(x)
                data_pts['y'].append(y)
            frame = pd.DataFrame(data_pts)

            # Setting range for k clusters
            max_k = int(ceil(len(pt_cld)/AVG_PT_CLD_SIZE) + 1)
            max_k = max_k if max_k < len(pt_cld) else len(pt_cld)

            # Determine optimal k value - Knee/Elbow locator
            k_clusters = range(1, max_k)
            k_sqr_dist = []
            for k in k_clusters:
                k_sqr_dist.append(k_means(frame, n_clusters=k)[2])
            try:
                k_loc = KneeLocator(k_clusters, k_sqr_dist, curve='convex',\
                    direction='decreasing')
                tgt_pos, label, _ = k_means(frame, n_clusters=k_loc.knee)
            except:
                # No Knee/Elbow detected - default to 1 cluster
                tgt_pos, label, _ = k_means(frame, n_clusters=1)

            # Remove targets that don't have enough particle points
            tgt_pts = {}
            for i in label:
                if i not in tgt_pts.keys():
                    tgt_pts[i] = 0
                else:
                    tgt_pts[i] += 1
            for k, v in tgt_pts.items():
                if v < MIN_TGT_SIZE:
                    tgt_pos = np.delete(tgt_pos, k, axis=0)
            
            # Update existing target positions or create new targets
            for pos in tgt_pos:
                tid, min_dist = (len(tgt_state) + 1), DIST_THRESHOLD
                for k, v in tgt_state.items():
                    dist = distance.euclidean(pos, v.x_hat)
                    if  dist < min_dist:
                        min_dist = dist
                        tid = k

                # Kalman Filter Algorithm
                if tid in tgt_state.keys():
                    tgt_state[tid].update(pos)
                else:
                    tgt_state[tid] = KalmanFilter(pos)

            # Remove targets that are no longer in view
            tmp = tgt_state.copy()
            for k, v in tgt_state.items():
                x, y = v.x_hat
                if (x < -self.lim_x) or (x > self.lim_x) or (y < 0) or \
                        (y > self.lim_y):
                    tmp.pop(k)
            tgt_state = tmp
            
        return tgt_state


if __name__ == '__main__':

    try:
        # Collect user input for deployment
        inputs = Data_Entry()
        if inputs.data_set == False:
            sys.exit('[GUI] Please save data values.')

        # Operation Mode: Live or Playback
        data_stream = Network_Client(inputs.server_ip) if inputs.mode == \
            LIVE_MODE else open(inputs.filename, 'rb')

        # Initialise the figure
        data_vis = Data_Visualiser()
        ((ax_radar, ax_image), (ax_heatmap, ax_occupancy)) = data_vis.get_axes()

        # Initialise all plots
        radar_plt       = Radar_Plot(ax_radar, inputs.x, inputs.y)
        image_plt       = Image_Plot(ax_image)
        heatmap_plt     = Heatmap_Plot(ax_heatmap, inputs.x, inputs.y)
        occupancy_plt   = Occupancy_Plot(ax_occupancy)

        prev_tgts = {}

        while True:
            # Retrieve Data Packet
            net_pkt = data_stream.data_received() if inputs.mode == LIVE_MODE \
                else p.load(data_stream)
            if net_pkt == None:
                continue

            # Network data filtered and converted for visualisation
            pkt = Network_Pkt(net_pkt, inputs, prev_tgts)
            prev_tgts = pkt.tgt_state

            # Update plot data
            active, inactive = heatmap_plt.update(pkt.targets, inputs.x, 
                inputs.y)
            radar_plt.update(active, inactive, pkt.particles)
            image_plt.update(pkt.img_arr)
            occupancy_plt.update(pkt.time_val, pkt.prediction, len(active), 
                len(inactive))

            # Refresh figure
            data_vis.refresh()

    except (tk.TclError, KeyboardInterrupt, EOFError):
        if inputs.mode == LIVE_MODE:
            data_stream.clean_up()
        elif inputs.mode == PLAYBACK_MODE:
            data_stream.close()
        heatmap_plt.save_summary(inputs.x, inputs.y, inputs.filename)
        sys.exit("[GUI] Terminated.")