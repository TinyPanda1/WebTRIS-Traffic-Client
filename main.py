from webtris_client import DataFetch, ClientWebTRIS

def main() -> None:
    print("Currently initializing the WebTRIS Client application")
    # creates the live getter methodology
    curr_fetcher = DataFetch()
    # call it into the client (object receives another object as an argument) - this is composition
    client = ClientWebTRIS(curr_fetcher)
    # instantiates the site + date from the requirements
    site_id = "461"
    objective_date = "19102025"
    

    print(f"Getting current data for the Site ID {site_id} on {objective_date}...")
    

    try:
        # Get a populated site object
        traffic_site = client.report_getter(site_id, objective_date)
        
        # prints out outcome to show the analysis methods
        print("\nTraffic Analysis Results: ")

        print(f"Site Name- {traffic_site.site_name}")

        print(f"Sum of Observations- {len(traffic_site)}")
        if len(traffic_site)>0:
            print(f"Overall Avg mph- {traffic_site.avg_mph()} mph")
            print(f"The Total Vehicle Volume- {traffic_site.total_vol()}")
            
            peak_hr = traffic_site.find_peak_hr()
            peak_vol = traffic_site.total_vol_hr(peak_hr)
            print(f"The Peak Traffic Hour is-  {peak_hr}:00 with {peak_vol} vehicles")
        else:
            print("No valid data found for the date given, can't calculate avg mph or total volume.")
            
    except Exception as error:
        print(f"\nAn error happened while running the program {error}")

# main method
if __name__ == "__main__":
    main()