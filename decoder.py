import struct

def decode(name, p):
        out = {}
        if name == 'fc_variant' and len(p) >= 4:
            out['firmware'] = p[:4].decode('ascii', errors='replace')
        elif name == 'fc_version' and len(p) >= 3:
            out['firmware_version'] = '.'.join(str(x) for x in p[:3])
        elif name == 'api_version' and len(p) >= 3:
            out['msp_api_version'] = f'{p[1]}.{p[2]}'
        elif name == 'attitude' and len(p) >= 6:
            roll, pitch, heading = struct.unpack_from('<hhh', p)
            out.update(roll_deg=roll / 10, pitch_deg=pitch / 10, heading_deg=heading)
        elif name == 'raw_gps' and len(p) >= 16:
            fix, sats, lat, lon, alt, speed, course = struct.unpack_from('<BBiihHH', p)
            out.update(gps_fix=fix, satellites=sats, latitude=lat / 1e7,
                       longitude=lon / 1e7, gps_altitude_m=alt,
                       ground_speed_mps=speed / 100, ground_course_deg=course / 10)
            if len(p) >= 18:
                out['gps_hdop_raw'] = struct.unpack_from('<H', p, 16)[0]
        elif name == 'analog' and len(p) >= 7:
            vbat, mah, rssi, amps = struct.unpack_from('<BHHh', p)
            out.update(legacy_voltage_v=vbat / 10, consumed_mah=mah,
                       rssi_raw=rssi, current_a=amps / 100)
            out['power_w'] = round(out['legacy_voltage_v'] * out['current_a'], 3)
        elif name == 'battery_state' and len(p) == 11:
            cells, capacity, legacy, mah, current, state, voltage = struct.unpack('<BHBHhBH', p)
            out.update(battery_cell_count=cells, battery_capacity_configured_raw=capacity,
                       legacy_voltage_v=legacy / 10, consumed_mah=mah,
                       current_a=current / 100, battery_state_raw=state,
                       battery_voltage_v=voltage / 100,
                       power_w=round(voltage * current / 10000, 3))
        elif name == 'nav_status' and len(p) >= 7:
            mode, state, action, waypoint, error, heading = struct.unpack_from('<5Bh', p)
            out.update(nav_mode_raw=mode, nav_state_raw=state, nav_waypoint_action_raw=action,
                       nav_waypoint_number=waypoint, nav_error_raw=error,
                       heading_hold_target_deg=heading)
        elif name == 'altitude' and len(p) >= 6:
            alt, vario = struct.unpack_from('<ih', p)
            out.update(estimated_altitude_m=alt / 100, vertical_speed_mps=vario / 100)
            if len(p) >= 10:
                out['baro_altitude_m'] = struct.unpack_from('<i', p, 6)[0] / 100
        elif name == 'comp_gps' and len(p) >= 4:
            dist, bearing = struct.unpack_from('<HH', p)
            out.update(distance_to_home_m=dist, direction_to_home_deg=bearing)
            if len(p) >= 5:
                out['gps_heartbeat'] = p[4]
        elif name == 'raw_imu' and len(p) >= 18:
            vals = struct.unpack_from('<9h', p)
            out.update(dict(zip(('acc_x_raw','acc_y_raw','acc_z_raw','gyro_x_raw',
                                 'gyro_y_raw','gyro_z_raw','mag_x_raw','mag_y_raw','mag_z_raw'), vals)))
        elif name in ('rc', 'servo', 'motor') and len(p) % 2 == 0:
            vals = struct.unpack('<' + 'H' * (len(p)//2), p)
            out.update({f'{name}_{i+1}_raw': v for i, v in enumerate(vals)})
        elif name == 'status' and len(p) >= 11:
            cycle, i2c, sensors, modes, profile = struct.unpack_from('<HHHIB', p)
            out.update(cycle_time_us=cycle, i2c_error_count=i2c,
                       sensor_mask=sensors, mode_flags_raw=modes, profile=profile)
        elif name == 'status_ex' and len(p) >= 16:
            cycle, i2c, sensors, modes, profile = struct.unpack_from('<HHHIB', p)
            out.update(cycle_time_us=cycle, i2c_error_count=i2c,
                       sensor_mask=sensors, mode_flags_raw=modes, profile=profile)
            load, arming_flags, calibration = struct.unpack_from('<HHB', p, 11)
            out.update(cpu_load_pct=load, arming_flags_raw=arming_flags,
                       armed=int(bool(arming_flags & (1 << 2))),
                       accelerometer_calibration_flags_raw=calibration)
        return out

    
