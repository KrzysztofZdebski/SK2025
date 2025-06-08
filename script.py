import re
import csv
from typing import Dict, List, Any

def parse_tmp_file(filepath: str) -> Dict[str, Dict[str, Any]]:
    """Parse the .tmp file containing sector data"""
    sectors = {}
    
    with open(filepath, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Split by SITEID sections
    site_sections = re.split(r'SITEID = ', content)[1:]  # Skip empty first element
    
    for section in site_sections:
        lines = section.strip().split('\n')
        site_id = lines[0].strip()
        
        sector_data = {}
        for line in lines[1:]:
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                sector_data[key] = value
        
        sectors[site_id] = sector_data
    
    return sectors

def parse_traffic_report(filepath: str) -> Dict[str, Dict[str, Any]]:
    """Parse the traffic loading report"""
    traffic_data = {}
    
    with open(filepath, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    # Find the data section (after the header with dashes)
    data_started = False
    for line in lines:
        if '--------- --------------- ----------------- ------------ --------- ---------------- --------------' in line:
            data_started = True
            continue
        
        if data_started and line.strip():
            # Parse the traffic data line
            parts = line.split()
            if len(parts) >= 7:  # Ensure we have enough columns
                sector_id = parts[0]
                circuit_traffic = parts[1]
                required_channels = parts[2]
                channels_set = parts[3]
                channel_shortfall = parts[4]
                blocking_prob = parts[5]
                packet_traffic = parts[6]
                
                traffic_data[sector_id] = {
                    'circuit_traffic': circuit_traffic,
                    'required_channels': required_channels,
                    'channels_set': channels_set,
                    'channel_shortfall': channel_shortfall,
                    'blocking_probability': blocking_prob,
                    'packet_traffic': packet_traffic
                }
    
    return traffic_data

def determine_station_from_sectors(sectors: List[str]) -> str:
    """Determine station name from sector IDs"""
    if not sectors:
        return ""
    
    # Extract common prefix (assuming format like ABAA0001, ABAA0002, etc.)
    first_sector = sectors[0]
    # Remove the last digit to get station base name
    return first_sector[:-1] if first_sector else ""

def create_csv_table(sectors_data: Dict, traffic_data: Dict, output_file: str):
    """Create CSV file matching the table structure from the image"""
    
    # Group sectors by station (assuming sectors with same prefix belong to same station)
    stations = {}
    for sector_id in sectors_data.keys():
        # Extract station name (remove last character which is sector number)
        station = sector_id[:-1]
        if station not in stations:
            stations[station] = []
        stations[station].append(sector_id)
    
    # Define CSV headers based on the corrected requirements
    headers = [
        'Nazwa stacji',  # Station name
        'ID sektora',    # Sector ID
        'Wys. stacji n.p.m. [m]',  # Station height above sea level
        'Moc nadajnika [W]/[dBW]',  # Transmitter power
        'Typ anteny nadawczej',     # Transmit antenna type
        'Azymut [°]',              # Azimuth
        'Pochylenie [°]',          # Tilt
        'Ruch generowany [mErl.]/[Mbps]',  # Generated traffic
        'Liczba potrzebnych kanałów',      # Required channels
        'Numery przydzielonych kanałów radiowych',  # Assigned channel numbers
        'Rzeczywiste prawdopodobieństwo blokady [%]',  # Actual blocking probability
        'Definicja sąsiedztwa dla HO (ID sektorów)'    # Neighborhood definition for HO
    ]
    
    rows = []
    
    for station, sector_list in stations.items():
        for i, sector_id in enumerate(sorted(sector_list)):
            sector_data = sectors_data.get(sector_id, {})
            traffic_info = traffic_data.get(sector_id, {})
            
            # Station name only for first sector of each station
            station_name = station if i == 0 else ""
            
            # Extract and convert relevant data
            height = sector_data.get('Site elevation(m)', '').strip()
            power_dbw = sector_data.get('Transmitter power(dBW)', '').strip()
            
            # Convert dBW to Watts if needed
            power_w = ""
            if power_dbw:
                try:
                    dbw_val = float(power_dbw)
                    watts = 10 ** (dbw_val / 10)
                    power_w = f"{watts:.2f}W/{power_dbw}dBW"
                except ValueError:
                    power_w = f"/{power_dbw}dBW"
            
            antenna_type = sector_data.get('Transmitter antenna type', '').strip()
            azimuth = sector_data.get('Transmit antenna azimuth orientation(degrees)', '').strip()
            tilt = sector_data.get('Transmit antenna mechanical beamtilt(degrees)', '').strip()
            
            # Traffic data
            circuit_traffic = traffic_info.get('circuit_traffic', '')
            packet_traffic = traffic_info.get('packet_traffic', '')
            traffic_combined = f"{circuit_traffic}mErl/{packet_traffic}Mbps" if circuit_traffic and packet_traffic else ""
            
            required_channels = traffic_info.get('required_channels', '')
            
            # Get the number of channels set from traffic data
            channels_set = traffic_info.get('channels_set', '')
            
            # Get the current blocking probability from traffic data
            blocking_probability = traffic_info.get('blocking_probability', '')
            # Handle the '*****' case for high blocking probability
            if blocking_probability == '*****':
                blocking_probability = '>99.99'
            
            row = [
                station_name,
                sector_id,
                height,
                power_w,
                antenna_type,
                azimuth,
                tilt,
                traffic_combined,
                required_channels,
                channels_set,
                blocking_probability,  # Now populated with Current Blocking Probability data
                ""   # HO neighborhood definition - not available in source data
            ]
            
            rows.append(row)
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(rows)
    
    print(f"CSV file created: {output_file}")
    print(f"Processed {len(rows)} sectors from {len(stations)} stations")

def main():
    # File paths
    tmp_file = "Project/tx_sector_data.tmp"
    traffic_file = "Project/reports/sector_traffic_loading.txt"
    output_csv = "sectors_table.csv"
    
    try:
        # Parse the input files
        print("Parsing sector data...")
        sectors_data = parse_tmp_file(tmp_file)
        
        print("Parsing traffic report...")
        traffic_data = parse_traffic_report(traffic_file)
        
        print("Creating CSV table...")
        create_csv_table(sectors_data, traffic_data, output_csv)
        
        print("\nSample of parsed data:")
        for sector_id in list(sectors_data.keys())[:2]:  # Show first 2 sectors
            print(f"\nSector {sector_id}:")
            print(f"  Location: {sectors_data[sector_id].get('Latitude(dd)', 'N/A')}, {sectors_data[sector_id].get('Longitude(dd)', 'N/A')}")
            print(f"  Azimuth: {sectors_data[sector_id].get('Transmit antenna azimuth orientation(degrees)', 'N/A')}°")
            if sector_id in traffic_data:
                print(f"  Traffic: {traffic_data[sector_id].get('circuit_traffic', 'N/A')} mErl")
                print(f"  Channels Set: {traffic_data[sector_id].get('channels_set', 'N/A')}")
                print(f"  Blocking Probability: {traffic_data[sector_id].get('blocking_probability', 'N/A')}%")
    
    except FileNotFoundError as e:
        print(f"Error: Could not find file - {e}")
    except Exception as e:
        print(f"Error processing files: {e}")

if __name__ == "__main__":
    main()