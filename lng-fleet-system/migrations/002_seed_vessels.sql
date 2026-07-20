-- Seed vessels for development & demo
INSERT INTO vessels (imo_number, name, flag, cargo_capacity_m3, build_year, engine_type, lng_tank_type, design_draft_m, design_speed_kn, eedi_attained, eexi_attained, scrubber_installed, scr_installed, shore_power_capable) VALUES
(9912345, 'LNG Innovator', 'PA', 174000, 2023, 'ME-GI', 'Membrane Type A', 12.0, 19.5, 2.85, 3.10, TRUE, TRUE, TRUE),
(9912346, 'LNG Pioneer', 'MH', 174000, 2022, 'X-DF', 'Membrane Type A', 12.0, 19.5, 2.90, 3.15, TRUE, TRUE, FALSE),
(9912347, 'LNG Voyager', 'BS', 180000, 2024, 'ME-GI', 'Membrane Type A', 12.5, 19.5, 2.75, 3.00, TRUE, TRUE, TRUE),
(9912348, 'LNG Champion', 'SG', 170000, 2021, 'X-DF', 'Membrane Type A', 11.8, 19.0, 3.00, 3.25, FALSE, TRUE, FALSE),
(9912349, 'LNG Navigator', 'PA', 145000, 2020, 'TFDE', 'MOSS', 11.5, 19.0, 3.20, 3.40, TRUE, FALSE, FALSE),
(9912350, 'LNG Horizon', 'MH', 138000, 2019, 'ST', 'Membrane Type B', 11.2, 18.5, 3.40, 3.55, TRUE, FALSE, FALSE),
(9912351, 'LNG Endeavor', 'BS', 174000, 2023, 'X-DF', 'Membrane Type A', 12.0, 19.5, 2.80, 3.05, TRUE, TRUE, TRUE),
(9912352, 'LNG Spirit', 'PA', 160000, 2022, 'ME-GI', 'Membrane Type A', 11.8, 19.2, 2.95, 3.20, FALSE, TRUE, FALSE),
(9912353, 'LNG Discovery', 'MH', 174000, 2024, 'X-DF', 'Membrane Type A', 12.0, 19.5, 2.78, 3.02, TRUE, TRUE, TRUE),
(9912354, 'LNG Enterprise', 'SG', 180000, 2024, 'ME-GI', 'Membrane Type A', 12.5, 19.5, 2.72, 2.98, TRUE, TRUE, TRUE);
