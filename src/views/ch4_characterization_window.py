"""Isolated acquisition routine for CH4 MFC characterization.

This module intentionally does not calculate or apply correction factors and never
selects a variable-gas MFC automatically.  Its CSV is designed to be joined with
the independently acquired SubOcean data by timestamp after the experiment.
"""

import csv
import os
import time
from datetime import datetime
from threading import Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..models.calculations import calculate_flows_for_total_flow


# Keep the starting experiment definitions in one obvious, easy-to-edit location.
# Keys are physical MFC identifiers; their addresses must be confirmed against the
# current plumbing before a run.
MFC_PROFILES = {
    "MFC_10ml": {"address": 8, "targets_ppm": [0, 5, 10, 15, 20, 25, 30]},
    "MFC_150ml": {"address": 5, "targets_ppm": [0, 20, 40, 60, 80, 100, 150, 200, 250, 300]},
    "MFC_1500ml": {"address": 3, "targets_ppm": [0, 100, 150, 200, 250, 300]},
}
AIR_MFC_ADDRESS = 20


class CH4CharacterizationWindow(tk.Toplevel):
    """Small, separate UI for CH4 characterization acquisition only."""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent_window = parent
        self.controller = controller
        self.title("CH4 MFC Characterization")
        self.geometry("720x640")
        self.resizable(True, True)

        self.default_directory = os.path.join(os.getcwd(), "characterization_data")
        self.directory_var = tk.StringVar(value=self.default_directory)
        self.mfc_var = tk.StringVar(value="MFC_10ml")
        self.source_ppm_var = tk.StringVar(value="5000")
        self.total_flow_var = tk.StringVar(value="1.0")
        self.dwell_seconds_var = tk.StringVar(value="60")
        self.reverse_var = tk.BooleanVar(value=True)
        self.stop_at_end_var = tk.BooleanVar(value=True)
        self.is_running = False
        self.run_thread = None
        self._setup_gui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_gui(self):
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="CH4 MFC characterization acquisition", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        ttk.Label(frame, text=("Uses MFC setpoints plus timestamps only. SubOcean data is not read "
                               "or processed by this application."), wraplength=650).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(frame, text="MFC under test:").grid(row=2, column=0, sticky="w", pady=4)
        selector = ttk.Combobox(frame, textvariable=self.mfc_var, state="readonly",
                                values=list(MFC_PROFILES), width=18)
        selector.grid(row=2, column=1, sticky="w", pady=4)
        selector.bind("<<ComboboxSelected>>", lambda event: self._update_preview())

        ttk.Label(frame, text="CH4 source concentration (ppm):").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.source_ppm_var, width=15).grid(row=3, column=1, sticky="w", pady=4)
        ttk.Label(frame, text="Use 5000 for the main dilution study; 101.1 for low-range checks.").grid(
            row=3, column=2, sticky="w", padx=8)

        ttk.Label(frame, text="Total flow (L/min):").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.total_flow_var, width=15).grid(row=4, column=1, sticky="w", pady=4)
        ttk.Label(frame, text="Air MFC address: 20").grid(row=4, column=2, sticky="w", padx=8)

        ttk.Label(frame, text="Dwell per step (seconds):").grid(row=5, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.dwell_seconds_var, width=15).grid(row=5, column=1, sticky="w", pady=4)

        ttk.Checkbutton(frame, text="Run decreasing ramp after increasing ramp", variable=self.reverse_var,
                        command=self._update_preview).grid(row=6, column=0, columnspan=3, sticky="w", pady=(8, 2))
        ttk.Checkbutton(frame, text="Set active air and CH4 MFCs to zero when finished/stopped",
                        variable=self.stop_at_end_var).grid(row=7, column=0, columnspan=3, sticky="w", pady=2)

        ttk.Label(frame, text="Output directory:").grid(row=8, column=0, sticky="w", pady=(12, 4))
        ttk.Entry(frame, textvariable=self.directory_var, state="readonly").grid(row=8, column=1, sticky="ew", pady=(12, 4))
        ttk.Button(frame, text="Browse…", command=self._select_directory).grid(row=8, column=2, padx=(8, 0), pady=(12, 4))

        ttk.Label(frame, text="Planned steps:").grid(row=9, column=0, sticky="nw", pady=(12, 4))
        self.preview = tk.Text(frame, height=12, width=72, state="disabled", font=("Consolas", 9))
        self.preview.grid(row=9, column=1, columnspan=2, sticky="nsew", pady=(12, 4))
        frame.rowconfigure(9, weight=1)

        controls = ttk.Frame(frame)
        controls.grid(row=10, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        self.start_button = ttk.Button(controls, text="Start characterization", command=self.start_routine)
        self.start_button.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.stop_button = ttk.Button(controls, text="Stop", command=self.stop_routine, state="disabled")
        self.stop_button.pack(side="left", fill="x", expand=True, padx=(4, 0))
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(frame, textvariable=self.status_var).grid(row=11, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self._update_preview()

    def _steps(self):
        ascending = list(MFC_PROFILES[self.mfc_var.get()]["targets_ppm"])
        if self.reverse_var.get() and len(ascending) > 1:
            return [(value, "increasing") for value in ascending] + [(value, "decreasing") for value in reversed(ascending[:-1])]
        return [(value, "increasing") for value in ascending]

    def _update_preview(self):
        profile = MFC_PROFILES[self.mfc_var.get()]
        text = "Selected MFC: {} (address {}) — automatic MFC switching is disabled\n\n".format(
            self.mfc_var.get(), profile["address"])
        text += "\n".join("{:2d}. {:10s} {:g} ppm".format(i, direction, target)
                          for i, (target, direction) in enumerate(self._steps(), 1))
        self.preview.config(state="normal")
        self.preview.delete("1.0", tk.END)
        self.preview.insert("1.0", text)
        self.preview.config(state="disabled")

    def _select_directory(self):
        selected = filedialog.askdirectory(title="Select characterization log directory", initialdir=self.directory_var.get())
        if selected:
            self.directory_var.set(selected)

    def start_routine(self):
        if not self.controller.is_connected():
            messagebox.showerror("Not connected", "Scan and connect the MFCs before starting.")
            return
        try:
            source_ppm = float(self.source_ppm_var.get())
            total_flow = float(self.total_flow_var.get())
            dwell_seconds = float(self.dwell_seconds_var.get())
        except ValueError:
            messagebox.showerror("Invalid configuration", "Source concentration, total flow, and dwell time must be numeric.")
            return
        if source_ppm <= 0 or total_flow <= 0 or dwell_seconds <= 0:
            messagebox.showerror("Invalid configuration", "Source concentration, total flow, and dwell time must all be positive.")
            return
        steps = self._steps()
        if any(target < 0 or target > source_ppm for target, _ in steps):
            messagebox.showerror("Unachievable target", "Every target must be between 0 and the CH4 source concentration.")
            return
        selected_name = self.mfc_var.get()
        selected_address = MFC_PROFILES[selected_name]["address"]
        required = {AIR_MFC_ADDRESS, selected_address}
        missing = required.difference(self.controller.instruments)
        if missing:
            messagebox.showerror("Missing MFC", "Required connected address(es): {}".format(", ".join(map(str, sorted(missing)))))
            return
        try:
            self._validate_flow_ranges(selected_address, source_ppm, total_flow, steps)
        except ValueError as error:
            messagebox.showerror("MFC range validation", str(error))
            return
        if not messagebox.askyesno(
            "Start CH4 characterization",
            "Run {} (address {}) with {} steps?\n\nOnly this MFC will be used as the CH4 MFC. "
            "SubOcean acquisition must already be running.".format(selected_name, selected_address, len(steps)),
        ):
            return
        os.makedirs(self.directory_var.get(), exist_ok=True)
        config = {
            "selected_name": selected_name, "selected_address": selected_address,
            "source_ppm": source_ppm, "total_flow": total_flow, "dwell_seconds": dwell_seconds,
            "steps": steps, "directory": self.directory_var.get(), "stop_at_end": self.stop_at_end_var.get(),
        }
        self.is_running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_var.set("Running")
        self.run_thread = Thread(target=self._run, args=(config,), daemon=True)
        self.run_thread.start()

    def _validate_flow_ranges(self, selected_address, source_ppm, total_flow, steps):
        """Reject a run whose requested setpoint is outside known MFC limits."""
        for address, label in ((AIR_MFC_ADDRESS, "synthetic-air MFC"), (selected_address, "selected CH4 MFC")):
            metadata = self.controller.get_instrument_metadata(address)
            unit = str(metadata.get("unit", "L/min"))
            min_native = float(metadata.get("min_flow", 0.0) or 0.0)
            max_native = float(metadata.get("max_flow", 0.0) or 0.0)
            for target, _direction in steps:
                q_air, q_ch4 = calculate_flows_for_total_flow(target, 0.0, source_ppm, total_flow)
                q_lmin = q_air if address == AIR_MFC_ADDRESS else q_ch4
                native = q_lmin * 1000.0 if "ml" in unit.lower() else q_lmin
                # Zero is an intended setpoint.  Nonzero values must honour both
                # the documented lower operating limit and the full-scale limit.
                if native > 1e-12 and native < min_native - 1e-12:
                    raise ValueError("{} would receive {:.6g} {}, below its minimum {:.6g} {} at {} ppm. "
                                     "Choose a different total flow or MFC.".format(label, native, unit, min_native, unit, target))
                if max_native > 0 and native > max_native + 1e-12:
                    raise ValueError("{} would receive {:.6g} {}, above its maximum {:.6g} {} at {} ppm. "
                                     "Choose a different total flow or MFC.".format(label, native, unit, max_native, unit, target))

    def stop_routine(self):
        if self.is_running and messagebox.askyesno("Stop characterization", "Stop after the current operation?"):
            self.is_running = False
            self.status_var.set("Stopping…")

    def _native_flow(self, address, flow_lmin):
        unit = self.controller.read_unit(address)
        return (flow_lmin * 1000.0 if "ml" in unit.lower() else flow_lmin), unit

    def _row(self, record_type, run_id, config, step_number, direction, target, q_air, q_ch4):
        ch4_native, ch4_unit = self._native_flow(config["selected_address"], q_ch4)
        air_native, air_unit = self._native_flow(AIR_MFC_ADDRESS, q_air)
        # Raw process values are retained as supplied by the MFC; native unit fields
        # make the result safe to interpret later.
        ch4_pv = self.controller.read_flow(config["selected_address"])
        air_pv = self.controller.read_flow(AIR_MFC_ADDRESS)
        return {
            "timestamp_local_iso": datetime.now().isoformat(timespec="microseconds"),
            "record_type": record_type, "run_id": run_id,
            "selected_mfc": config["selected_name"], "selected_mfc_address": config["selected_address"],
            "air_mfc_address": AIR_MFC_ADDRESS, "step_number": step_number, "ramp_direction": direction,
            "target_ch4_ppm": target, "source_ch4_ppm": config["source_ppm"],
            "ch4_mfc_setpoint_l_min": q_ch4, "air_mfc_setpoint_l_min": q_air,
            "total_flow_l_min": config["total_flow"],
            "ch4_mfc_setpoint_native": ch4_native, "ch4_mfc_native_unit": ch4_unit,
            "air_mfc_setpoint_native": air_native, "air_mfc_native_unit": air_unit,
            "ch4_mfc_pv_raw": ch4_pv, "air_mfc_pv_raw": air_pv,
        }

    def _run(self, config):
        run_id = "ch4_mfc_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(config["directory"], run_id + ".csv")
        fields = ["timestamp_local_iso", "record_type", "run_id", "selected_mfc", "selected_mfc_address",
                  "air_mfc_address", "step_number", "ramp_direction", "target_ch4_ppm", "source_ch4_ppm",
                  "ch4_mfc_setpoint_l_min", "air_mfc_setpoint_l_min", "total_flow_l_min",
                  "ch4_mfc_setpoint_native", "ch4_mfc_native_unit", "air_mfc_setpoint_native", "air_mfc_native_unit",
                  "ch4_mfc_pv_raw", "air_mfc_pv_raw"]
        completed = False
        try:
            with open(log_path, "w", newline="", encoding="utf-8") as log_file:
                writer = csv.DictWriter(log_file, fieldnames=fields)
                writer.writeheader()
                # Prevent stale setpoints on the other characterization MFCs
                # from contributing gas. This is deliberately not selection:
                # only config['selected_address'] is used for every step.
                for profile in MFC_PROFILES.values():
                    address = profile["address"]
                    if address != config["selected_address"] and address in self.controller.instruments:
                        self.controller.set_flow(address, 0.0)
                for step_number, (target, direction) in enumerate(config["steps"], 1):
                    if not self.is_running:
                        break
                    q_air, q_ch4 = calculate_flows_for_total_flow(target, 0.0, config["source_ppm"], config["total_flow"])
                    # This routine deliberately never calls automatic instrument selection.
                    if not self.controller.set_flow(AIR_MFC_ADDRESS, q_air):
                        raise RuntimeError("Could not set synthetic-air MFC at address {}".format(AIR_MFC_ADDRESS))
                    if not self.controller.set_flow(config["selected_address"], q_ch4):
                        raise RuntimeError("Could not set selected CH4 MFC at address {}".format(config["selected_address"]))
                    writer.writerow(self._row("setpoint_applied", run_id, config, step_number, direction, target, q_air, q_ch4))
                    log_file.flush()
                    self.after(0, lambda s=step_number, t=target: self.status_var.set(
                        "Step {}/{}: {} ppm setpoint applied".format(s, len(config["steps"]), t)))
                    deadline = time.monotonic() + config["dwell_seconds"]
                    while self.is_running and time.monotonic() < deadline:
                        writer.writerow(self._row("raw_mfc_sample", run_id, config, step_number, direction, target, q_air, q_ch4))
                        log_file.flush()
                        time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
                completed = self.is_running
        except Exception as error:
            error_text = str(error)
            self.after(0, lambda message=error_text: messagebox.showerror("Characterization error", message))
        finally:
            self.is_running = False
            if config["stop_at_end"]:
                self.controller.set_flow(config["selected_address"], 0.0)
                self.controller.set_flow(AIR_MFC_ADDRESS, 0.0)
            state = "completed" if completed else "stopped or failed"
            self.after(0, lambda: self._finish(state, log_path))

    def _finish(self, state, log_path):
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_var.set("Run {}. Log: {}".format(state, log_path))
        if hasattr(self.parent_window, "print_to_command_output"):
            self.parent_window.print_to_command_output("CH4 characterization {}: {}".format(state, log_path), "success" if state == "completed" else "warning")

    def _on_close(self):
        if self.is_running:
            messagebox.showwarning("Characterization running", "Stop the run before closing this window.")
            return
        self.destroy()
