#!/bin/python

"""
Main user interface and controller for Tinbergen.
"""

import sys
import os
import gobject
import gtk
import gst
import tbdatamodel
import string

NO_TIME = float('nan')

if __name__ == '__main__':
    # Get the path to this script using sys.argv[0]
    script_dir = os.path.dirname(sys.argv[0])
else:
    # Get the path to this script using __file__
    script_dir = os.path.dirname(__file__)
mainwin_gladefile = os.path.join(script_dir, 'tb_mainwin.glade')

class MainUI:
    """
    A class to open a window for coding a Tinbergen project.
    """
    key_dispatch = {'new obs': gtk.gdk.keyval_from_name('Tab'),
                    'step forward': gtk.gdk.keyval_from_name('Right'),
                    'step back': gtk.gdk.keyval_from_name('Left'),
                    'play/pause': gtk.gdk.keyval_from_name('space'),
                    'speed x2': gtk.gdk.keyval_from_name('backslash'),
                    'speed x1': gtk.gdk.keyval_from_name('bracketright'),
                    'speed x.5': gtk.gdk.keyval_from_name('bracketleft')}
    hotkey_list = [gtk.gdk.keyval_from_name(c) for c in string.ascii_letters+string.digits]
    
    def __init__(self, project):
        self.project = project
        self._cur_observer = None
        self._cur_video = None
        self._cur_video_rate = 1.0 # Ought to be able to do this by querying
                                   # the player, but I can't figure out how
        self.current_modified = False
        # Load UI from Glade file:
        builder = gtk.Builder()
        builder.add_from_file(mainwin_gladefile)
        # Get references to relevant objects as attributes of self:
        ui_objects = ['main_win','observer_combo','file_nav','behavior_nav',
                      'video_area', 'play_button', 'time_scale']
        for item in ui_objects:
            setattr(self, item, builder.get_object(item))
        
        self.time_scale.set_digits(3)
        # Connect signals from UI to methods of self:
        builder.connect_signals(self)
        self.behavior_entry_cell = gtk.CellRendererText()
        self.configure_observer_combo()
        self.configure_file_nav()
        self.configure_behavior_nav()
        
        self.player = gst.element_factory_make('playbin2')
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect('message::eos', self.on_video_end)
        bus.connect('message::state-changed', self.on_player_state_change)
        bus.connect('sync-message::element', self.on_attach_video_window)
        
        self.time_update_handle = None
        self.current_framerate = None
        self.main_win.show()
    
    def get_current_observer(self):
        "Returns the current observer."
        return self._cur_observer
    
    def set_current_observer(self, new):
        """
        Sets the current observer. If new is not a valid observer code for the
        project, sets to no current observer.
        """
        if new == self._cur_observer:
            return
        # We are about to close the observations, so save them first.
        self.save_current_obs()
        observer_codes = [obs['code'] for obs in self.project.observers]
        if new not in observer_codes:
            new = None
        self._cur_observer = new
        # Update the Observer combobox to reflect the change.
        combo_active = self.observer_combo.get_active()
        combo_model = self.observer_combo.get_model()
        combo_items = [row[0] for row in combo_model]
        if combo_active < 1:
            combo_current = None
        else:
            combo_current = combo_items[combo_active]
        if new != combo_current:
            # Only change the combobox if necessary, to avoid looping
            if new is None:
                self.observer_combo.set_active(0)
            else:
                new_active = combo_items.index(new)
                self.observer_combo.set_active(new_active)
        # Now that the observer has changed, open observations again.
        self.open_observations()
    
    def get_current_video(self):
        "Returns the current video file."
        return self._cur_video
    
    def set_current_video(self, new):
        """
        Set the current video file.
        """
        if new == self._cur_video:
            return
        if new not in self.project.video_files:
            new = None
        # Close the video
        self.player.set_state(gst.STATE_NULL)
        # We're about to close the current observations, so save first
        self.save_current_obs()
        self._cur_video = new
        # If the selected video is not the new video, update the selection
        nav_selection = self.file_nav.get_selection()
        nav_model, nav_iter = nav_selection.get_selected()
        if nav_iter is None:
            nav_current = None
        else:
            nav_current = nav_model.get_value(nav_iter, 0)
        if new != nav_current:
            if new is None:
                nav_selection.unselect_all()
            else:
                for ind in xrange(len(nav_model)):
                    if new == nav_model[ind][0]:
                        nav_selection.select_path(ind)
                        break
        if new is not None:
            # Open the new video
            video_path = self.project.join_video_path(new)
            self.player.set_property('uri', 'file://' + video_path)
            self.player.set_state(gst.STATE_PAUSED)
        self.open_observations()
    
    def get_current_time(self):
        """
        For the currently open video, get the current time, in seconds. If there
        is no video open, return 0.
        """
        try:
            nanosecs, format = self.player.query_position(gst.FORMAT_TIME)
            return float(nanosecs) / gst.SECOND
        except gst.QueryError:
            return 0
    
    def set_current_time(self, time):
        """
        Seek to a given time in the video.
        """
        if time < 0:
            time = 0.0
        self.player.seek(self.get_video_rate(), gst.FORMAT_TIME,
                     gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE,
                     gst.SEEK_TYPE_SET, int(time * gst.SECOND),
                     gst.SEEK_TYPE_NONE, 0)
    
    def get_video_duration(self):
        """
        Get the duration of the current video, in seconds.
        """
        try:
            nanosecs, format = self.player.query_duration(gst.FORMAT_TIME)
            return float(nanosecs) / gst.SECOND
        except gst.QueryError:
            return 0
    
    def get_video_rate(self):
        "Get the current relative playback rate. 1.0 is normal speed."
        return self._cur_video_rate
    
    def set_video_rate(self, rate):
        "Set the current relative playback rate. 1.0 normal speed."
        try:
            nanosecs, format = self.player.query_position(gst.FORMAT_TIME)
            self.player.seek(rate, gst.FORMAT_TIME,
                     gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE,
                     gst.SEEK_TYPE_SET, nanosecs,
                     gst.SEEK_TYPE_NONE, 0)
            self._cur_video_rate = rate
        except gst.QueryError:
            return
    
    def can_edit_observations(self):
        "Returns True if the observations are currently editable."
        return self._cur_observer is not None and self._cur_video is not None
    
    def is_video_playing(self):
        status,state,pending = self.player.get_state(0)
        return state == gst.STATE_PLAYING
    
    def is_video_loaded(self):
        status,state,pending = self.player.get_state(0)
        return state in [gst.STATE_PAUSED, gst.STATE_PLAYING]
    
    #------- CONFIGURE OBJECTS -------
    def configure_observer_combo(self):
        # Create model and cell renderers for the observer combobox
        model = gtk.ListStore(str)
        #model.append(['<Observer...>'])
        model.append([''])
        cell = gtk.CellRendererText()
        self.observer_combo.pack_start(cell, True)
        #self.observer_combo.add_attribute(cell, 'text', 0)
        self.observer_combo.set_cell_data_func(cell, self.render_observer_combo)
        self.observer_combo.set_model(model)
        for observer in self.project.observers:
            model.append([observer['code']])
    
    def configure_file_nav(self):
        # Create columns and cell renderers for the file_nav treeview
        nav = self.file_nav
        file_selection = nav.get_selection()
        file_selection.set_mode(gtk.SELECTION_SINGLE)
        file_selection.connect('changed', self.on_select_file)
        #file_selection.set_select_function(self.on_select_file)
        filename_column = gtk.TreeViewColumn('Movie File')
        observed_column = gtk.TreeViewColumn('Observed')
        nav.append_column(filename_column)
        nav.append_column(observed_column)
        name_cell = gtk.CellRendererText()
        filename_column.pack_start(name_cell, True)
        filename_column.add_attribute(name_cell,'text',0)
        name_cell.set_property('size-points', 9)
        obs_cell = gtk.CellRendererText()
        observed_column.pack_start(obs_cell, True)
        observed_column.set_cell_data_func(obs_cell, self.render_file_observers)
        obs_cell.set_property('size-points', 9)
        self.make_file_model()
    
    def configure_behavior_nav(self):
        # Create columns and cell renderers for the behavior_nav treeview
        nav = self.behavior_nav
        time_col = gtk.TreeViewColumn('Time')
        entry_col = gtk.TreeViewColumn('Entry')
        behav_col = gtk.TreeViewColumn('Behavior')
        time_col.set_sort_column_id(0)
        nav.append_column(time_col)
        nav.append_column(entry_col)
        nav.append_column(behav_col)
        time_cell = gtk.CellRendererText()
        time_cell.set_property('size-points', 9)
        entry_cell = self.behavior_entry_cell
        entry_cell.set_property('size-points', 9)
        entry_cell.set_property('editable', True)
        entry_cell.connect('edited', self.on_edit_entry)
        name_cell = gtk.CellRendererText()
        name_cell.set_property('size-points', 9)
        value_cell = gtk.CellRendererText()
        value_cell.set_property('size-points', 9)
        time_col.pack_start(time_cell,True)
        #time_col.add_attribute(time_cell,'text',0)
        time_col.set_cell_data_func(time_cell, self.render_behav_time)
        entry_col.pack_start(entry_cell,True)
        entry_col.set_cell_data_func(entry_cell, self.render_behav_entry)
        behav_col.pack_start(name_cell)
        behav_col.pack_start(value_cell)
        behav_col.set_cell_data_func(name_cell, self.render_behav_name)
        behav_col.set_cell_data_func(value_cell, self.render_behav_value)
        self.open_observations()
    
    #------- TREE MODEL FACTORIES -------
    def make_file_model(self):
        # Create a list store to hold files in the current project and attach
        # it to the file_nav
        file_store = gtk.ListStore(str)
        for f in self.project.video_files:
            file_store.append([f])
        self.file_nav.set_model(file_store)
    
    def make_behaviors_model(self, obslist):
        # Create a list store to hold observations for the current video and
        # attach it to the behavior_nav
        store = gtk.ListStore(float, object)
        for obs in obslist:
            store.append([float(obs.get('time','nan')), obs])
        self.behavior_nav.set_model(store)
    
    #------- EVENT CALLBACKS -------
    def on_main_win_destroy(self, window):
        self.player.set_state(gst.STATE_NULL)
        if self.time_update_handle is not None:
            gobject.source_remove(self.time_update_handle)
        self.save_current_obs()
        gtk.main_quit()
    
    def on_observer_combo_changed(self, combobox):
        active = combobox.get_active()
        if active < 1:
            current = None
        else:
            model = combobox.get_model()
            current = model[active][0]
        if self._cur_observer != current:
            self.set_current_observer(current)
    
    def on_select_file(self, selection):
        nav_model, nav_iter = selection.get_selected()
        if nav_iter is None:
            selected = None
        else:
            selected = nav_model.get_value(nav_iter, 0)
        if self._cur_video != selected:
            self.set_current_video(selected)
    
    def on_main_key_press(self, window, event):
        if self.behavior_entry_cell.get_property('editing'):
            return False
        keyval = event.keyval
        if keyval == self.key_dispatch['new obs']:
            self.make_new_observation()
            #self.main_win.handler_block_by_func(self.on_main_key_press)
            return True
        elif keyval == self.key_dispatch['step forward']:
            self.step_video_forward()
            #return True
            # It would be better to directly manipulate the player and let the
            # slider inherit the new time, but step events don't seem to work
            # quite right in GStreamer, or at least I don't understand them
            # properly.
            #self.time_scale.emit('move-slider', gtk.SCROLL_STEP_RIGHT)
            return True
        elif keyval == self.key_dispatch['step back']:
            self.step_video_back()
            #return True
            #self.time_scale.emit('move-slider', gtk.SCROLL_STEP_LEFT)
            return True
        elif keyval == self.key_dispatch['play/pause']:
            self.toggle_playback()
            return True
        elif keyval == self.key_dispatch['speed x2']:
            self.set_video_rate(2.0)
            return True
        elif keyval == self.key_dispatch['speed x1']:
            self.set_video_rate(1.0)
            return True
        elif keyval == self.key_dispatch['speed x.5']:
            self.set_video_rate(0.5)
            return True
        elif keyval in self.hotkey_list:
            keyname = gtk.gdk.keyval_name(keyval)
            self.make_new_observation(keyname)
            return True
        else: # Unhandled key press
            return False
    
    def on_behavior_nav_key_press(self, nav, event):
        delkeys = [gtk.gdk.keyval_from_name(s) for s in ['BackSpace', 'Delete']]
        if event.keyval in delkeys:
            # Delete the currently selected entry
            (model, treeiter) = nav.get_selection().get_selected()
            model.remove(treeiter)
            self.current_modified = True
            return True
    
    def on_start_edit_entry(self, cell, editable, path):
        pass
        #self.main_win.handler_block_by_func(self.on_main_key_press)
    
    def on_edit_entry(self, cell, path, new_entry):
        #self.main_win.handler_unblock_by_func(self.on_main_key_press)
        # Actually edit the entry
        obs = self.project.ethogram.parse_entry(new_entry)
        model = self.behavior_nav.get_model()
        model[path][1] = obs
        self.current_modified = True
    
    def on_video_end(self, bus, message):
        self.player.set_state(gst.STATE_PAUSED)
    
    def on_select_observation(self, selection):
        pass
    
    def on_play_button_clicked(self, button):
        self.toggle_playback()
    
    def on_time_scale_value_changed(self, slider):
        self.set_current_time(slider.get_value())
    
    def on_time_update(self):
        scale = self.time_scale
        scale.handler_block_by_func(self.on_time_scale_value_changed)
        #scale.set_range(0, self.get_video_duration())
        scale.set_value(self.get_current_time())
        scale.handler_unblock_by_func(self.on_time_scale_value_changed)
        return True
    
    def on_attach_video_window(self, bus, message):
        if message.structure is None:
            return
        message_name = message.structure.get_name()
        if message_name == 'prepare-xwindow-id':
            imagesink = message.src
            imagesink.set_property('force-aspect-ratio', True)
            gtk.gdk.threads_enter()
            imagesink.set_xwindow_id(self.video_area.window.xid)
            gtk.gdk.threads_leave()
    
    def on_player_state_change(self, bus, message):
        if message.src != self.player:
            return
        prev_state,new_state,pending_state = message.parse_state_changed()
        if pending_state != gst.STATE_VOID_PENDING:
            # State transition is still in progress; let's wait until it's done
            return
        if prev_state == gst.STATE_READY:
            # A new video has been loaded and is all ready
            buf = self.player.get_property('frame')
            caps = buf.get_caps()
            capstr = caps.get_structure(0)
            self.current_framerate =  float(capstr['framerate'])
            # Set up the time scale for the new video
            scale = self.time_scale
            scale.handler_block_by_func(self.on_time_scale_value_changed)
            scale.set_range(0, self.get_video_duration())
            scale.set_increments(1/self.current_framerate, 1)
            scale.set_value(self.get_current_time())
            scale.handler_unblock_by_func(self.on_time_scale_value_changed)
        elif new_state == gst.STATE_PAUSED:
            # The video was playing and is now paused
            # we should update button icon and such
            # Stop auto-updating the time slider
            if self.time_update_handle is not None:
                gobject.source_remove(self.time_update_handle)
            self.on_time_update()
        elif new_state == gst.STATE_PLAYING:
            # The video has started playing
            # Update button icon and such
            # Set an auto-updater for the time slider
            self.time_update_handle = gobject.timeout_add(100,
                                                          self.on_time_update)
    
    #------- VIDEO PLAYBACK CONTROL -------
    def step_video_forward(self):
        if not self.is_video_loaded():
            return
        step_secs = 1/self.current_framerate
        step_nanosecs = int(step_secs * gst.SECOND)
        step = gst.event_new_step(gst.FORMAT_TIME, step_nanosecs, 1, True,False)
        self.player.send_event(step)
        #self.on_time_update()
    
    def step_video_back(self):
        if not self.is_video_loaded():
            return
        step_secs = 1/self.current_framerate
        step_nanosecs = int(step_secs * gst.SECOND)
        # Try this: reverse pipeline, step, restore pipeline
        #self.player.seek(-1.0, gst.FORMAT_TIME,
        #                 gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE,
        #                 gst.SEEK_TYPE_NONE, 0,
        #                 gst.SEEK_TYPE_NONE, 0)
        #step = gst.event_new_step(gst.FORMAT_TIME, step_nanosecs, 1, True,False)
        #self.player.send_event(step)
        #self.player.seek(1.0, gst.FORMAT_TIME,
        #                 gst.SEEK_FLAG_ACCURATE,
        #                 gst.SEEK_TYPE_NONE, 0,
        #                 gst.SEEK_TYPE_NONE, 0)
        # That did not work. Let's try manually seeking.
        try:
            cur_nanosecs, format = self.player.query_position(gst.FORMAT_TIME)
        except gst.QueryError:
            # Just give up.
            return
        new_time = cur_nanosecs - step_nanosecs
        if new_time < 0:
            new_time = 0
        self.player.seek(self.get_video_rate(), gst.FORMAT_TIME,
                     gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_ACCURATE,
                     gst.SEEK_TYPE_SET, new_time,
                     gst.SEEK_TYPE_NONE, 0)
        #self.player.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH,
        #                        cur_nanosecs - step_nanosecs)
        #self.on_time_update()
    
    def toggle_playback(self):
        status,state,pending = self.player.get_state(0)
        if state == gst.STATE_PAUSED:
            self.player.set_state(gst.STATE_PLAYING)
        elif state == gst.STATE_PLAYING:
            self.player.set_state(gst.STATE_PAUSED)
    
    #------- TREE CELL RENDERER CALLBACKS -------
    def render_observer_combo(self, column, cell, model, treeiter):
        obs_code = model.get_value(treeiter, 0)
        if obs_code:
            obs_name = self.project.get_observer_name(obs_code)
            obs_name += ' ({0})'.format(obs_code)
        else:
            obs_name = '<Observer...>'
        cell.set_property('text', obs_name)
    
    def render_file_observers(self, column, cell, model, treeiter):
        filename = model.get_value(treeiter, 0)
        observers = self.project.get_video_observers(filename)
        observer_str = ', '.join(observers)
        cell.set_property('text', observer_str)
    
    def render_behav_time(self, column, cell, model, treeiter):
        time = model.get_value(treeiter, 0)
        cell.set_property('text', '{:.3f}'.format(time))
    
    def render_behav_entry(self, column, cell, model, treeiter):
        obs = model.get_value(treeiter, 1)
        cell.set_property('text', obs.get('entry', ''))
    
    def render_behav_name(self, column, cell, model, treeiter):
        obs = model.get_value(treeiter, 1)
        cell.set_property('text', obs.get('name', ''))
    
    def render_behav_value(self, column, cell, model, treeiter):
        obs = model.get_value(treeiter, 1)
        cell.set_property('text', obs.get('value', ''))
    
    #------- FILE NAVIGATION -------
    def make_new_observation(self, entry=None):
        if not self.can_edit_observations():
            return
        nav = self.behavior_nav
        model = nav.get_model()
        new_item_path = len(model)
        if entry is None:
            model.append([self.get_current_time(), {}])
            do_edit = True
            #edit_column = nav.get_column(1)
            #nav.set_cursor(new_item_path, edit_column, start_editing=True)
            #nav.grab_focus()
        else:
            obs = self.project.ethogram.parse_entry(entry)
            model.append([self.get_current_time(), obs])
            self.current_modified = True
            do_edit = False
        nav.set_cursor(new_item_path, nav.get_column(1), start_editing=do_edit)
    
    def save_current_obs(self):
        # Save them if they've been modified
        if not self.current_modified:
            return
        obs_model = self.behavior_nav.get_model()
        obslist = []
        for row in obs_model:
            obs = row[1]
            obs['time'] = row[0]
            obslist.append(obs)
        self.project.save_obslist(self._cur_video, self._cur_observer, obslist)
    
    def open_observations(self):
        # Get behavior_nav entry cell renderer
        entry_col = self.behavior_nav.get_column(1)
        entry_cell = entry_col.get_cell_renderers()[0]
        # Load observations for the current observer and video from file
        cur_video = self.get_current_video()
        cur_observer = self.get_current_observer()
        obslist = self.project.load_obs_from_file(cur_video, cur_observer)
        self.make_behaviors_model(obslist)
        entry_cell.set_property('editable', self.can_edit_observations())
        entry_cell.connect('editing-started', self.on_start_edit_entry)
        self.current_modified = False

if __name__ == '__main__':
    import sys
    project_file = sys.argv[1]
    project = tbdatamodel.Project(project_file)
    gtk.gdk.threads_init()
    MainUI(project)
    gtk.main()
