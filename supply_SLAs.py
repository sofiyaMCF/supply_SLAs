#import necessary packages
import pandas as pd
from statistics import mean
import plotly.express as px
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import streamlit as st
import warnings
warnings.filterwarnings('ignore')



custom_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Open+Sans&display=swap');

        body {
            font-family: 'Arial', 'Open Sans', sans-serif;
        }

        .custom-markdown {
            font-size: 16px;
            line-height: 1.5;
            max-width: 800px;
            width: 100%;
        }
        
        .custom-text-area {
            font-family: 'Arial', 'Open Sans', sans-serif;
            font-size: 16px;
            line-height: 1.5;
            padding: 10px;
            width: 100%;
            box-sizing: border-box;
            white-space: pre-wrap;
        }
        
        .larger-font {
            font-size: 18px;
            font-weight: bold;
        }
        
        .largest-font {
            font-size: 28px;
            font-weight: bold;
        }
        
        .title {
            font-family: 'Arial', 'Open Sans', sans-serif;
            font-size: 36px;
            font-weight: bold;
        }
        
    </style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

#add the Michelin banner to the top of the application, if the image link breaks you can correct this by copying and pasting an alternative image url in the ()
st.image("https://www.tdtyres.com/wp-content/uploads/2018/12/kisspng-car-michelin-man-tire-logo-michelin-logo-5b4c286206fa03.5353854915317177300286.png")

#set the application title to 'Supply Chain SlAs'
st.markdown('<div class="custom-text-area title">{}</div>'.format('Supply Chain SLAs'), unsafe_allow_html=True)


#create uplaod box for the supply chain data file
supply_chain_file = st.file_uploader("Choose supply chain report file", type=['xlsx'])

#make sure the supply chain file is uploaded before processing begins
if supply_chain_file is not None:
    #determine file type and process accordingly
    if supply_chain_file.name.endswith('.csv'):
        #read CSV file and write to supply chain file
        raw_supply_chain_data = pd.read_csv(supply_chain_file)
    
    elif supply_chain_file.name.endswith('.xlsx'):
        #read Excel file
        raw_supply_chain_data = pd.read_excel(supply_chain_file)
    #if neither an excel or csv are uploaded return this error to the user
    else:
        st.error("Unsupported file type. Please upload an Excel file.")

#create uplaod box for the supply chain data file
sales_file = st.file_uploader("Choose sales report file", type=['xlsx'])


#make sure the sales file is uploaded before processing begins
if sales_file is not None:
    #determine file type and process accordingly
    if sales_file.name.endswith('.csv'):
        #read CSV file and write to supply chain file
        raw_sales_data = pd.read_csv(sales_file)
    
    elif sales_file.name.endswith('.xlsx'):
        #read Excel file
        raw_sales_data = pd.read_excel(sales_file)
    #if neither an excel or csv are uploaded return this error to the user
    else:
        st.error("Unsupported file type. Please upload an Excel file.")

#if raw_sales_data and raw_supply_chain_data exist (the correct files were uploaded) continue with the rest of the function
if supply_chain_file and sales_file:
    with st.spinner('Processing...'):
    
        #create a list of shipping reference numbers
        shipping_list = list(set(raw_supply_chain_data['Shipping Details: Ref No.'].values.tolist()))

        #rename the sales 'Opportunity' column to "Opportunity Name" to match the supply chain excel
        raw_sales_data.rename(columns={'Opportunity Name': 'Opportunity'}, inplace=True)

        #merge the sales and supply chain data into one dataframe
        raw_data = pd.merge(raw_supply_chain_data, raw_sales_data, on='Opportunity', how='outer')

        #remove any sales demo account orders from the dataframe
        raw_data = raw_data[~((raw_data['Account Name_x'] == 'MCFNA Sales Demo Account'))].copy()

        #create lists to store change in times (time measurements in hours)
        #list of time (days) from when an order is closed won to created
        created_timestamps = []
        #list of time (hours) from when order is created to confirmed
        confirmed_timestamps = []
        #list of time (hours) when an order moves to order accepted (from out of stock or confirmed)
        order_accept_timestamps = []
        #list of time (hours) of when an order moves from order accepted to shipped
        ord_accept_shipped_timestamps = []
        #list of time (hours) of when an order moves from confirmed to shipped
        confirmed_shipped_timestamps = []
        #list of time (hours) of when an order moves from confirmed to shipped
        confirm_shipped_timestamps = []
        #list of time (hours) that an order is out of stock
        out_of_stock_timestamps = []

        #create lists to store order reference numbers
        #list of cases that were created
        orders_created = []
        #list of cases that were confirmed
        orders_confirmed = []
        #list of orders that went from confirmed to accepted
        orders_accepted = []
        #list of orders that went from accepted to shipped
        orders_accepted_shipped = []
        #list of orders that were confirmed and shipped
        orders_confirmed_shipped = []
        #list of orders that were accepted but not shipped
        orders_accepted_not_shipped = []
        #list of orders that had out of stock parts
        orders_out_of_stock = []
        #list of orders that have been cancelled
        cancelled_orders = []
        
        #create lists to store order status edit dates
        #list of created edit dates
        created_dates = []
        #list of confirmed edit dates
        confirmed_dates = []
        #list of confirmed to accepted edit dates
        accepted_dates = []
        #list of accepted to shipped edit dates
        accepted_shipped_dates = []
        #list of confirmed to shipped edit dates
        confirmed_shipped_dates = []
        #list of out of stock edit dates
        out_of_stock_dates = []

        #dictionary of shipping reference numbers and the account name
        account_names = dict(zip(raw_data['Shipping Details: Ref No.'].values.tolist(), raw_data['Account Name_x'].values.tolist()))
        #dictionary of the shipping reference numbers and the opportunity name
        opportunity_names = dict(zip(raw_data['Shipping Details: Ref No.'].values.tolist(), raw_data['Opportunity'].values.tolist()))
        #dictionary of closed won timestamps
        closed_ts = dict(zip(raw_data['Shipping Details: Ref No.'].values.tolist(), raw_data['Closed won date'].values.tolist()))
        #create dictionary of closed won dates
        closed_won = {}
        #dictionary of opportunity types
        opp_type = dict(zip(raw_data['Shipping Details: Ref No.'].values.tolist(), raw_data['Opportunity Type'].values.tolist()))
        #dictionary of asset types
        asset_type = dict(zip(raw_data['Shipping Details: Ref No.'].values.tolist(), raw_data['Asset Type'].values.tolist()))

        #the closed won date column timestamps are automatically converted to nanseconds, create a function to convert them to seconds
        #pull the shipping reference number and the timestamp from the closed won timestamp dictionary
        for ref_no, timestamp in closed_ts.items():
            #if the timestamp is none, leave it as none
            if timestamp is None:
                closed_won[ref_no] = None
            else:
                try:
                    #convert nanoseconds to seconds
                    dt = datetime.fromtimestamp(timestamp / 1e9)
                    #write the new converted timestamp to the previous nanosecond timestamp
                    closed_won[ref_no] = dt
                #if there is an error converting, assign None value to the timestamp
                except (OSError, ValueError) as e:
                    closed_won[ref_no] = None

        #create a function that writes the timestamp into a string for legible reading, takes the form year-month-day hours:minutes:seconds
        def format_datetime(dt):
            if dt is None:
                return 'None'
            return dt.strftime('%Y-%m-%d %H:%M:%S')

        #format the closed_won dictionary as strings using the previous function
        closed_won = {key: format_datetime(value) for key, value in closed_won.items()}

        #create a function to convert values into timestamps for later calculations
        def convert_to_timestamp(value):
            #if the values is a string, convert to a timestamp
            if isinstance(value, str):
                return pd.Timestamp(value)
            #if the value is a timestamp, do not alter the value
            elif isinstance(value, pd.Timestamp):
                return value
            #if neither then the value is unsupported and raise an error
            else:
                raise ValueError("Unsupported value type")

        #check if values are nan (non-existant/None) and return True or False Boolean
        def is_nan(value):
            try:
                return np.isnan(value)
            except TypeError:
                return False

        #remove nan keys from the following dictionaries (only want dictionary keys to be shipping refference numbers)
        account_names = {k: v for k, v in account_names.items() if not is_nan(k)}
        opportunity_names = {k: v for k, v in opportunity_names.items() if not is_nan(k)}
        closed_won = {k: v for k, v in closed_won.items() if not is_nan(k)}
        opp_type = {k: v for k, v in opp_type.items() if not is_nan(k)}
        asset_type = {k: v for k, v in asset_type.items() if not is_nan(k)}

 
        #check the statuses and timestamps of each case by shipping reference number
        #iterate through list of shipping reference numbers
        for value in shipping_list:
            #create variables to store timestamp information
            #timestamp storing when an order is created
            created_timestamp = None
            #timestamp storing when an order is confirmed
            confirmed_timestamp = None
            #timestamp storing when an order is accepted
            ord_accept_timestamp = None
            #timestamp storing when an order is shipped
            shipped_timestamp = None
            #timestamp when an order is out of stock entered as new value
            nv_out_of_order_timestamp = None
            #timestamp when an order is out of stock is old value (changes from out of stock)
            ov_out_of_order = None

            #iterate through the raw_data dataframe
            for ind in raw_data.index:

                #collect timestamp information from each row related to case
                if raw_data['Shipping Details: Ref No.'][ind] == value:
                    #find and store when an order is created
                    if raw_data['Field / Event'][ind] == 'Created.' : 
                        created_timestamp = raw_data['Edit Date'][ind]
                    #find and store when an order is confirmed
                    if raw_data['New Value'][ind] == 'Confirmed' and raw_data['Old Value'][ind] == 'Not confirmed':
                        confirmed_timestamp = raw_data['Edit Date'][ind]
                    #find and store when an order is accepted
                    if raw_data['New Value'][ind] == 'Order accepted' and raw_data['Old Value'][ind] == 'Confirmed':
                        ord_accept_timestamp = raw_data['Edit Date'][ind]
                    #find and store when order labled as out of stock
                    if raw_data['New Value'][ind] == 'Out of stock':
                        nv_out_of_order_timestamp = raw_data['Edit Date'][ind]
                    #find and store when order changed from out of stock
                    if raw_data['Old Value'][ind] == 'Out of stock':
                        ov_out_of_order_timestamp = raw_data['Edit Date'][ind]
                    #find and store when an order is out of stock to when it is accepted
                    if raw_data['New Value'][ind] == 'Order accepted' and raw_data['Old Value'][ind] == 'Out of stock':
                        ord_accept_timestamp = raw_data['Edit Date'][ind]
                    #find and store when an order is accepted to shipped
                    if raw_data['New Value'][ind] == 'Shipped' and raw_data['Old Value'][ind] == 'Order accepted':
                        shipped_timestamp = raw_data['Edit Date'][ind]
                    #add cancelled orders to list of cancelled orders
                    if raw_data['Status'][ind] == 'Cancelled':
                        cancelled_orders.append(value)


            #check that order created timestamp and order confirmed timestamp exist
            if created_timestamp and closed_ts[value]:
                #convert the closed_won timestamp string into a timestamp
                closed_won_timestamp = convert_to_timestamp(closed_won[value])
                #create a variable storing the difference between closed won and order created
                created_ts = created_timestamp - closed_won_timestamp
                #change the time difference into days (from Timestamp delta) for later calculations and add to created timestamp list
                created_timestamps.append(round(created_ts.total_seconds()/86400,1))
                #add shipping reference number to the list of confirmed orders
                orders_created.append(value)
                #add created edit date to created_dates
                created_dates.append(created_timestamp)

            if created_timestamp and confirmed_timestamp:
                #create a variable storing time difference between order created and confirmed
                confirmed_ts = confirmed_timestamp - created_timestamp
                #change the time difference into days (from Timestamp delta) for later calculations and add to confirmed timestamp list
                confirmed_timestamps.append(round(confirmed_ts.total_seconds()/86400,1))
                #add shipping reference number to the list of confirmed orders
                orders_confirmed.append(value)
                #add confirmed edit date to confirmed_dates
                confirmed_dates.append(confirmed_timestamp)

            #check that order confirmed and order accepted timestamps exist
            if confirmed_timestamp and ord_accept_timestamp:
                #create a variable storing time difference between order confirmed and accepted
                ord_accept_ts = ord_accept_timestamp - confirmed_timestamp
                #change the time difference into days (from Timestamp delta) for later calculations and add to accepted timestamp list
                order_accept_timestamps.append(round(ord_accept_ts.total_seconds()/86400,1))
                #add shipping reference number to list of accepted orders
                orders_accepted.append(value)
                #add accepted edit date to accepted_dates
                accepted_dates.append(ord_accept_timestamp)

            #check that order accepted and order shipped timestamps exist
            if ord_accept_timestamp and shipped_timestamp:
                #create a variable storing time difference between order accepted and shipped
                shipped_accept_ts = shipped_timestamp - ord_accept_timestamp
                #change the time difference into days (from Timestamp delta) for later calculations and add to orders accepted and shipped timestamp list
                ord_accept_shipped_timestamps.append(round(shipped_accept_ts.total_seconds()/86400,1))
                #add shipping reference number to list of accepted and shipped orders
                orders_accepted_shipped.append(value)
                #add shipped_timestamp edit date to accepted_shipped_dates
                accepted_shipped_dates.append(shipped_timestamp)

            #check that order shipped timestamp and order confirmed timestamps exist
            if shipped_timestamp and confirmed_timestamp:
                #create a variable storing time difference between order confirmed and shipped
                shipped_confirmed_ts = shipped_timestamp - confirmed_timestamp
                #change the time difference into days (from Timestamp delta) for later calculations and add to orders confirmed and shipped timestamp list
                confirmed_shipped_timestamps.append(round(shipped_confirmed_ts.total_seconds()/86400,1))
                #add shipping reference number to list of confirmed and shipped orders
                orders_confirmed_shipped.append(value)
                #add shipped_timestamp edit date to confirmed_shipped_dates
                confirmed_shipped_dates.append(shipped_timestamp)


            #check that out of stock timestamp exists for both new value and old value to see how much time is added to the order
            if nv_out_of_order_timestamp and ov_out_of_order_timestamp:
                #create a variable to store the amount of time the order is out of stock
                out_of_stock_ts = ov_out_of_order_timestamp - nv_out_of_order_timestamp
                #change the time difference into hours (from Timestamp delta) for later calculations and add to out of stock timestamp list
                out_of_stock_timestamps.append(round(out_of_stock_ts.total_seconds()/86400,1))
                #add shipping reference number to list of out of stock orders
                orders_out_of_stock.append(value)
                #add nv_out_of_stock edit date to confirmed_shipped_dates
                out_of_stock_dates.append(nv_out_of_order_timestamp)

            #check for orders that were accepted but never shipped
            if not shipped_timestamp and ord_accept_timestamp:
                orders_accepted_not_shipped.append(value)
        
        #create a function that will convert timestamps into month and year, this will later be used to create the date column
        def month_year(alist):
            #create an empty list
            new_list = []
            #iterate through called list
            for value in alist:
                #pull the month and year from the timestamp and assign them to variables
                year = value.year
                month_name = value.strftime('%B')
                #add the month and year to the empty list as strings
                new_list.append(f'{year}: {month_name}')
            return new_list
        
        #convert all the date lists of timestamps to year and month strings
        created_dates = month_year(created_dates)
        confirmed_dates = month_year(confirmed_dates)
        accepted_dates = month_year(accepted_dates)
        accepted_shipped_dates = month_year(accepted_shipped_dates)
        confirmed_shipped_dates = month_year(confirmed_shipped_dates)
        out_of_stock_dates = month_year(out_of_stock_dates)
                
                
        #create list of shipping references + timestamps and status type
        status_type_timestamp_ref_num = []
        #create a list of edit date dictionaries
        edit_dates = []

        #create dictionary of orders and their created times (checking time from closed won to shipping reference created)
        created_times = dict(zip(orders_created, created_timestamps))
        #create list of status type created
        status_type_created = ['Closed Won to Created' for value in orders_created]
        status_type_created = dict(zip(orders_created, status_type_created))
        #add to list of status types, timestamps and reference numbers
        status_type_timestamp_ref_num.append((created_times, status_type_created))
        #create dictionary of created edit dates and shipping reference numbers
        created_edits = dict(zip(orders_created, created_dates))
        edit_dates.append(created_edits)

        #create dictionary of orders and their confirmation times
        confirmed_times = dict(zip(orders_confirmed, confirmed_timestamps))
        #create list of status type confirmation
        status_type_confirmation = ['Created to Confirmed' for value in orders_confirmed]
        status_type_confirmation = dict(zip(orders_confirmed, status_type_confirmation))
        #add to list of status types, timestamps and reference numbers
        status_type_timestamp_ref_num.append((confirmed_times, status_type_confirmation))
        #create dictionary of confirmed edits dates and shipping reference numbers
        confirmed_edits = dict(zip(orders_confirmed, confirmed_dates))
        edit_dates.append(confirmed_edits)

        #create dictionary of orders and their accepted time
        accepted_times = dict(zip(orders_accepted, order_accept_timestamps))
        #create list of status type accepted
        status_type_accepted = ['Confirmed to Accepted' for value in orders_accepted]
        status_type_accepted = dict(zip(orders_accepted, status_type_accepted))
        #add to list of status types, timestamps and reference numbers
        status_type_timestamp_ref_num.append((accepted_times, status_type_accepted))
        #create dictionary of accepted edits dates and shipping reference numbers
        accepted_edits = dict(zip(orders_accepted, accepted_dates))
        edit_dates.append(accepted_edits)


        #create dictionary of orders and their time from the order being accepted to shipped
        accepted_shipped_times = dict(zip(orders_accepted_shipped, ord_accept_shipped_timestamps))
        #create list of status type accepted to shipped
        status_type_accepted_shipped = ['Accepted to Shipped' for value in orders_accepted_shipped]
        status_type_accepted_shipped = dict(zip(orders_accepted_shipped, status_type_accepted_shipped))
        #add to list of status types, timestamps and reference numbers
        status_type_timestamp_ref_num.append((accepted_shipped_times, status_type_accepted_shipped))
        #create dictionary of accepted shipped edits dates and shipping reference numbers
        accepted_shipped_edits = dict(zip(orders_accepted_shipped, accepted_shipped_dates))
        edit_dates.append(accepted_shipped_edits)

        #create dictionary of orders and their time from order being confirmed to being shipped
        confirmed_shipped_times = dict(zip(orders_confirmed_shipped, confirmed_shipped_timestamps))
        #create list of status type confirmed to shipped
        status_type_confirmed_shipped = ['Confirmed to Shipped' for value in orders_confirmed_shipped]
        status_type_confirmed_shipped = dict(zip(orders_confirmed_shipped, status_type_confirmed_shipped))
        #add to list of status types, timestamps and reference numbers
        status_type_timestamp_ref_num.append((confirmed_shipped_times, status_type_confirmed_shipped))
        #create dictionary of confirmed shipped edits dates and shipping reference numbers
        confirmed_shipped_edits = dict(zip(orders_confirmed_shipped, confirmed_shipped_dates))
        edit_dates.append(confirmed_shipped_edits)

        #create a dictionary indicating orders that were out of stock
        out_of_stock_order_times = dict(zip(orders_out_of_stock, out_of_stock_timestamps))
        #create list of status type out of stock
        status_type_out_of_order = ['Out of Stock' for value in orders_out_of_stock]
        status_type_out_of_order = dict(zip(orders_out_of_stock, status_type_out_of_order))
        #add to list of status types, timestamps and reference numbers
        status_type_timestamp_ref_num.append((out_of_stock_order_times, status_type_out_of_order))
        #create dictionary of out of order edit dates and shipping reference numbers
        out_of_order_edits = dict(zip(orders_out_of_stock, out_of_stock_dates))
        edit_dates.append(out_of_order_edits)

        #create dictionary of orders that were not shipped
        #create list indicating how many orders were not shipped
        not_shipped = ['Not Shipped' for value in orders_accepted_not_shipped]
        orders_not_shipped = dict(zip(orders_accepted_not_shipped, not_shipped))

        #create a dictionary indicating unusual orders
        cancelled = ['Cancelled' for value in cancelled_orders]
        cancelled_orders = dict(zip(cancelled_orders, cancelled))

        #extract all keys from dictionaries
        all_keys = sorted(set(created_times.keys()).union(confirmed_times.keys()).union(accepted_times.keys()).union(accepted_shipped_times.keys()).union(confirmed_shipped_times.keys()).union(out_of_stock_order_times.keys()).union(orders_not_shipped.keys()).union(cancelled_orders.keys()))
 
   

        #create a total_times dictionary that will store the total amount of time it took for an opportunity to enter closed_won to be shopped to the customer
        total_times = {}
        #for shipping reference number in the all_keys dictionary 
        for key in all_keys:
            #total time begins at 0
            total_time = 0
            #add the amount of time it took for the order to be created (closed won to created)
            if key in created_times.keys():
                total_time += created_times[key]
            #add the time it took for an order to be confirmed (created to confirmed)
            if key in confirmed_times.keys():
                total_time += confirmed_times[key]
            #add the time it took for an order to be accepted (confirmed to accepted)
            if key in accepted_times.keys():
                total_time += accepted_times[key]
            #add the ammount of time it took the order to be shipped (accepted to shipped)
            if key in accepted_shipped_times.keys():
                total_time += accepted_shipped_times[key]
            #round the total time to 1 decimal point
            total_times[key] = round(total_time,1)

        #convert each dictionary to a series with all keys from the dictionaries (ensures we have series/columns with the shipping reference numbers as our primary key/index)
        def dict_to_series(d, keys):
            return pd.Series({key: d.get(key, None) for key in keys})

        #create list of empty dataframes that will be propegated with information from the dictionaries
        create_order_info = pd.DataFrame()
        confirm_order_info = pd.DataFrame()
        accept_order_info = pd.DataFrame()
        confirm_ship_order_info = pd.DataFrame()
        accept_ship_order_info = pd.DataFrame()
        out_of_stock_order_info = pd.DataFrame()
        df_list = [create_order_info, confirm_order_info, accept_order_info, confirm_ship_order_info, accept_ship_order_info, out_of_stock_order_info]

        #propegate the dataframes with dictionaries that we have converted to series, iterate through our main list of dictionaries as we iterate through the dataframe list to make sure our information matches, it is very important we are mindful of the dataframe and dictionary order
        for i, df in enumerate(df_list):
            df_list[i] = pd.DataFrame({
                'Order Status Change': dict_to_series(status_type_timestamp_ref_num[i][1], all_keys),
                'Time Elapsed (Days)': dict_to_series(status_type_timestamp_ref_num[i][0], all_keys),
                'Account Name': dict_to_series(account_names, all_keys),
                'Opportunity Name': dict_to_series(opportunity_names, all_keys),
                'Opportunity Type': dict_to_series(opp_type, all_keys),
                'Asset Type': dict_to_series(asset_type, all_keys),
                'Closed Won': dict_to_series(closed_won, all_keys),
                'Order Out of Stock': dict_to_series(status_type_out_of_order, all_keys),
                'Order Shipped': dict_to_series(orders_not_shipped, all_keys),
                'Cancelled Order': dict_to_series(cancelled_orders, all_keys),
                'Date' : dict_to_series(edit_dates[i], all_keys),
                'Total Time (Days)': dict_to_series(total_times, all_keys)
            })

            #fill in the None values with relevant information
            for ind in df_list[i].index:
                if df_list[i]['Order Shipped'][ind] == None:
                    df_list[i]['Order Shipped'][ind] = 'Yes'
                if df_list[i]['Cancelled Order'][ind] == None:
                    df_list[i]['Cancelled Order'][ind] = 'No'
                if df_list[i]['Order Out of Stock'][ind] == None:
                    df_list[i]['Order Out of Stock'][ind] = 'No'
                if df_list[i]['Asset Type'][ind] == None:
                    df_list[i]['Asset Type'][ind] = 'N/A'
                if df_list[i]['Opportunity Type'][ind] == None:
                    df_list[i]['Opportunity Type'][ind] = 'N/A'


            #set the index name to 'Shipping Reference Number'
            df_list[i].index.name = 'Shipping Reference Number'
            #reset the index so it is a column
            df_list[i].reset_index(inplace = True)


            #split the date column into year and month for sorting
            df_list[i][['Year', 'Month']] = df_list[i]['Date'].str.split(': ', expand=True)

            # Convert column to numeric, forcing errors to NaN
            df_list[i]['Year'] = pd.to_numeric(df_list[i]['Year'], errors='coerce')

            # Fill NaN with a default value
            df_list[i]['Year'].fillna(0, inplace=True)

            #convert 'Year' to integer and 'Month' to categorical with a specific order
            df_list[i]['Year'] = df_list[i]['Year'].astype(int)

            #define the month order
            month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December']

            #sort the dataframe months by the month order previously defined
            df_list[i]['Month'] = pd.Categorical(df_list[i]['Month'], categories=month_order, ordered=True)

            #sort DataFrame by 'Year' and 'Month'
            df_list[i] = df_list[i].sort_values(by=['Year', 'Month'])


        #limit out of order dataframe to only include out of stock orders, most orders are in stock and this skews results
        df_list[5] = df_list[5][(df_list[5]['Order Out of Stock'] == 'Out of Stock')].copy()

        #create main order info dataframe that holds all info from all dataframes in our df_list
        order_info = pd.concat(df_list, ignore_index=True)
        #sort order info dataframe by year and month
        order_info = order_info.sort_values(by=['Year', 'Month'])
        
        #drop year and month columns from order info and all other dataframes in df_list
        order_info.drop(columns=['Year', 'Month'], inplace=True)
        for df in df_list:
            df = df.drop(columns=['Year', 'Month'], inplace=True)

        #create a total_time_order_info dataframe that includes information about the total lifetime of the orders, use the confirm_order_info dataframe as a base as all orders with shipping reference numbers are confirmed (largest volume of data)
        total_time_order_info = df_list[1].drop(columns = ['Order Status Change','Time Elapsed (Days)'])
        #rename the 'Total Time (Days)' column to 'Time Elapsed (Days)' so this dataframe is consistent with the format of the other dataframes
        total_time_order_info.rename(columns = {'Total Time (Days)': 'Time Elapsed (Days)'}, inplace = True)
        #add this total time dataframe to our dataframe list
        df_list.append(total_time_order_info)

        #create a dataframe of order information for the 'Order Lifetime' visualization, excludes order information related to 'Confirmed to Accepted' and 'Accepted to Shipped' (double counting days)
        order_info_con_ship = order_info[
        ~((order_info['Order Status Change'] == 'Confirmed to Accepted') | 
          (order_info['Order Status Change'] == 'Accepted to Shipped'))].copy()

        #create a dataframe of order information for 'Detailed Order Lifetime' visualization, excludes order information related to 'Confirmed to Shipped' (double counting days)
        order_info_con_accept_ship  = order_info[
        ~((order_info['Order Status Change'] == 'Confirmed to Shipped'))].copy()

        #create empty graphs to store histograms for each of the dataframes
        create_fig = go.Figure()
        confirm_fig = go.Figure()
        accepted_fig = go.Figure()
        confirm_ship_fig = go.Figure()
        accept_ship_fig = go.Figure()
        out_of_order_fig= go.Figure()
        total_time_fig = go.Figure()

        #create a histogram list of the empty dataframes which later will be iterated through to automate histogram creation
        hist_list = [create_fig, confirm_fig, accepted_fig, confirm_ship_fig, accept_ship_fig, out_of_order_fig, total_time_fig]

        #iterate through the data frames
        for i in range(len(df_list)):
            #create the histograms with shipping reference number as the x-axis and time elapsed as the y-axis, create a marginal visualization that allows you to get all information
            #related to the shipping reference number (marginal = rug), hover_data
            hist_list[i] = px.histogram(df_list[i], x= "Shipping Reference Number", y="Time Elapsed (Days)", color = 'Date', marginal="rug", hover_data= df_list[i].columns)

        #create empty graphs to store boxplots for each of the dataframes
        create_box = go.Figure()
        confirm_box = go.Figure()
        accepted_box = go.Figure()
        confirm_ship_box = go.Figure()
        accept_ship_box = go.Figure()
        out_of_order_box= go.Figure()
        total_time_box = go.Figure()

        #create a box list of empty dataframes which will later be iterated through to automate boxplot creation
        box_list = [create_box, confirm_box, accepted_box, confirm_ship_box, accept_ship_box, out_of_order_box, total_time_box]


        #iterate through the data frames
        for i in range(len(df_list)):
            #create the boxplots with time elapsed as the x-axis, create a marginal visualization that allows you to get all information
            #related to the shipping reference number (marginal = rug), hover_data
            box_list[i] = px.box(df_list[i], x= "Time Elapsed (Days)", color = 'Date', hover_data= df_list[i].columns)

       
    #custom colors assigned for Order Lifetime Graphs (want graphs/processes to be color matched)
        custom_colors = {
            'Closed Won to Created': '#636efa',
            'Created to Confirmed': '#00cc96',
            'Confirmed to Accepted': '#FFA15A',
            'Accepted to Shipped': '#19d3f3',
            'Confirmed to Shipped': '#ab63fa',
            'Out of Stock': '#FF6692'
        }

        #create histogram for the 'Order Lifetime' data, excludes confirmed to accepted and accepted to shipped
        con_ship_fig = px.histogram(order_info_con_ship, x= "Shipping Reference Number", y="Time Elapsed (Days)", color="Order Status Change", marginal="rug",
                       hover_data = order_info_con_ship.columns, color_discrete_map = custom_colors)

        #add this histogram to the list of histograms
        hist_list.append(con_ship_fig)
        
        #create boxplot for the 'Order Lifetime' data, excludes confirmed to accepted and accepted to shipped
        con_ship_box = px.box(order_info_con_ship, x ="Time Elapsed (Days)", color="Order Status Change",
                           hover_data = order_info_con_ship.columns, color_discrete_map = custom_colors)
        
        #add this boxplot to the list of boxplots
        box_list.append(con_ship_box)

        #create histogram for the 'Detailed Order Lifetime' data, excludes confirmed to shipped
        con_accept_ship_fig = px.histogram(order_info_con_accept_ship, x= "Shipping Reference Number", y="Time Elapsed (Days)", color="Order Status Change", marginal="rug",
                       hover_data = order_info_con_accept_ship.columns, color_discrete_map = custom_colors)
        #add this histogram to the list of histograms
        hist_list.append(con_accept_ship_fig)
        
        #create boxplot for the 'Detailed Order Lifetime' data, excludes confirmed to shipped
        con_accept_ship_box = px.box(order_info_con_accept_ship, x= "Time Elapsed (Days)", color="Order Status Change",
                   hover_data = order_info_con_accept_ship.columns, color_discrete_map = custom_colors)
        #add this boxplot to the list of boxplots
        box_list.append(con_accept_ship_box)

        #create a list of titles for the histograms and boxplots, iterate through this list to assign titles to graphs
        title_list = ['Time Elapsed Closed Won to Created', 'Time Elapsed Created to Confirmed', 'Time Elapsed Confirmed to Accepted', 'Time Elapsed Confirmed to Shipped', 'Time Elapsed Accepted to Shipped', 'Time Elapsed Out of Stock', 'Total Order Time', 'Order Lifetime', 'Detailed Order Lifetime']

        #format the graphs, add titles and assign a graph height
        for i in range(len(hist_list)):
            hist_list[i].update_layout(
                title={
                    'text': f'{title_list[i]}<br><sup>Hover over top bar for additional order information</sup>', #assign title
                    'x': 0.5,  #center title
                    'xanchor': 'center',  #center title
                    'yanchor': 'top',  #anchor title to the top
                    'font': {'size': 20},  #main title font size
                },
                title_font_size=24,  #main title font size
                title_font_color="black",  #main title font color
                yaxis_title='Time Elapsed (Days)',  #customize the y-axis title
                font=dict(
                    size=12,  #global font size
                    color="black"  #global font color
                ),
                #width=1200,
                height=700, #size the graph
            )

        #makes the 'Order Lifetime' and 'Detailed Order Lifetime' graphs taller
        hist_list[7].update_layout(height=900)
        hist_list[8].update_layout(height=900)

        #format the boxplot graphs
        for i in range(len(box_list)):
            box_list[i].update_layout(
                title={
                    'text': f'{title_list[i]}<br><sup>Hover over points for additional order information</sup>', #assign title
                    'x': 0.5,  #center title
                    'xanchor': 'center',  #center title
                    'yanchor': 'top',  #anchor title to the top
                    'font': {'size': 24, 'color': 'black'},  # title font size and color
                },
                xaxis_title='Time Elapsed (Days)',  #customize the x-axis title
                font=dict(
                    size=12,  #global font size
                    color="black"  #global font color
                ),
                #width=1200,
                height=600, #size the graph
            )


        #create output describing the statistics of each dataframe, include mean, median, std. dev. count, ect.
        #create empty outputs to assign text to later
        create_output = ''
        confirm_output = ''
        accept_output = ''
        confirm_ship_output = ''
        accept_ship_output = ''
        out_of_order_output = ''
        total_time_output = ''

        #add empty output to output_list
        output_list = [create_output, confirm_output, accept_output, confirm_ship_output, accept_ship_output, out_of_order_output, total_time_output]

        #create a list describing whats happening with the shipping reference numbers
        ship_ref_action_list = ['Shipping Reference Numbers Created', 'Shipping Reference Numbers Confirmed', 'Shipping Reference Numbers Accepted', 'Shipping Reference Numbers Shipped', 'Shipping Reference Numbers Shipped', 'Out of Stock Shipping Reference Numbers', 'Shipping Reference Numbers Completed']

        #iterate through the list of dataframes and pull statistics and propegate the empty output strings with stats
        for i in range(len(df_list)):
            descriptive_stats = df_list[i]['Time Elapsed (Days)'].describe()
            text = f'''
                    Number of {ship_ref_action_list[i]}: {round(descriptive_stats[0], 0).astype(int)}

                    Average Number of Days from {title_list[i][12:]}: {round(descriptive_stats[1], 1)}

                    Minimum Number of Days from {title_list[i][12:]}: {round(descriptive_stats[3], 1)}

                    First Quartile Number of Days from {title_list[i][12:]}: {round(descriptive_stats[4], 1)}

                    Median Number of Days from {title_list[i][12:]}: {round(descriptive_stats[5], 1)}

                    Third Quartile Number of Days from {title_list[i][12:]}: {round(descriptive_stats[6], 1)}

                    Maximum Number of Days from {title_list[i][12:]}: {round(descriptive_stats[7], 1)}

                    Standard Deviation (Days) from {title_list[i][12:]}: {round(descriptive_stats[2], 1)}
            '''
            #assign the text to the values in the list of outputs
            output_list[i] = text


            
        #create an empty list to store dataframes, rounded dataframes 'Time Elapsed (Days)' and 'Total Time (Days)' columns rounded to the nearest day
        rounded_df_list= []
        
        #iterate through the df_list
        for df in df_list:
            #round the dataframe columns to the nearest day
            rounded_df = df.round()
            
            #add the rounded dataframe to the rounded_df_list
            rounded_df_list.append(rounded_df)

            
        #create a list to store the grouped dataframes, these grouped dataframes will hold the dataframes that 
        grouped_df_list = []

        #iterate throught the rounded_df_list to select dataframes
        for df in rounded_df_list:
            #create a list of sub_dfs (this will hold the grouped dataframes that are split by month)
            sub_df_list = []

            #select all the dates from the df
            a_month_keys = list(set(df['Date'].dropna().values.tolist()))

            #for a date in the list of dates
            for month_key in a_month_keys:
                #reduce the grouped dataframe to only entries that occured on the month_key (month and year = month_key)
                monthly_df = df[df['Date'] == month_key]

                #create empty dictionary that will store days elapsed as key, and count, date (month and year) and shipping reference numbers as values
                days_dict = {}

                #create keys for the days_dict dictioanry, keys are distinct values from the 'Time Elapsed (Days)' column
                days_elapsed = list(set(monthly_df['Time Elapsed (Days)'].dropna().values.tolist()))

                #iterate through the keys
                for day_key in days_elapsed:
                    #create variable to hold order count
                    count = 0

                    #create list to hold shipping reference numbers/accounts
                    ship_ref_accounts = []

                    #create list to hold the number of shipping reference numbers/accounts
                    num_accounts = []

                    #iterate through the rounded dataframe
                    for ind in monthly_df.index:
                        #if the value in the 'Time Elapsed (Days)' column is equal to the days_elapsed key
                        if monthly_df['Time Elapsed (Days)'][ind] == day_key:
                            #add to the order count variable
                            count += 1

                            #add the shipping reference number and the account name to the list of shipping ref numbers/accounts, in the format Shipping Ref Number: Account Name
                            ship_ref_accounts.append(f"{monthly_df['Shipping Reference Number'][ind]}: {monthly_df['Account Name'][ind]}")

                    #append num_accounts with the shipping reference number count, in the form Shipping Ref 1, Shipping Ref 2...
                    for i in range(1, (len(ship_ref_accounts) + 1)):
                        num_accounts.append(f'Shipping Ref {i}')

                    #create a dictionary of the shipping reference count and the matched account
                    ship_ref_accounts_dict = dict(zip(num_accounts, ship_ref_accounts))

                    #turn the dictionary into a list of tuples
                    ship_ref_accounts_list = [[key, value] for key, value in ship_ref_accounts_dict.items()]

                    #add day_key as the key and the count, date, and shipping reference numbers/accounts as the value to the days_dict dictionary
                    days_dict[day_key] = [count, month_key, ship_ref_accounts_list ]

                #iterate through the days_dict items    
                for key, value in days_dict.items():
                    #create an empty list to hold the information to format (this will become the hover text on the scatterplots)
                    text_list = []

                    #add the shipping reference numbers/accounts from the dictionary value to the text_list
                    for sublist in value[2]:
                        text_list.append(f'{sublist[0]}: {sublist[1]}')

                    #if a dictionary key has more than 31 associated shipping reference accounts/numbers the hover text becomes too large to display, create alternative text
                    if len(text_list) > 31:
                        text_list = ['Too many references to display']

                    #join the shipping reference numbers/accounts list into one large text, split the list items with a break for formatting
                    value[2] = "<br>".join(text_list)

                #name the columns
                columns = ['Order Count', 'Date', 'Shipping Details']

                #create a dataframe from the days_dict dictionary
                sub_df = pd.DataFrame.from_dict(days_dict, orient='index')

                #assign column names to the dataframe
                sub_df.columns = columns

                #name the index
                sub_df.index.name = 'Time Elapsed (Days)'

                #reset the index so it becomes a column
                sub_df.reset_index(inplace = True)

                #cast the days into integers
                sub_df['Time Elapsed (Days)'] = sub_df['Time Elapsed (Days)'].fillna(0).astype(int)

                #add this grouped monthly dataframe to the sub_df_list
                sub_df_list.append(sub_df)

            #concatenate all the monthly dataframes into one large grouped dataframe
            grouped_df = pd.concat(sub_df_list, ignore_index=True)

            #add the final grouped dataframe to the list of grouped dataframes
            grouped_df_list.append(grouped_df)
            
            
            
        for df in grouped_df_list:
            #split the date column into year and month for sorting
            df[['Year', 'Month']] = df['Date'].str.split(': ', expand=True)

            #convert column to numeric, forcing errors to NaN
            df['Year'] = pd.to_numeric(df['Year'], errors='coerce')

            #fill NaN with a default value
            df['Year'].fillna(0, inplace=True)

            #convert 'Year' to integer and 'Month' to categorical with a specific order
            df['Year'] = df['Year'].astype(int)

            #define the month order
            month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December']

            #sort the dataframe months by the month order previously defined
            df['Month'] = pd.Categorical(df['Month'], categories=month_order, ordered=True)

            #sort dataframe by 'Year' and 'Month'
            df.sort_values(by=['Year', 'Month'], inplace = True)

            #drop the redundant 'Year' and 'Month' columns
            df.drop(columns = ['Year', 'Month'], inplace= True)            
            
            
        #create empty graphs that will be propegated with grouped dataframe info turned into scatterplots
        create_days_fig = go.Figure()
        confirm_days_fig = go.Figure()
        accept_days_fig = go.Figure()
        confirm_ship_days_fig = go.Figure()
        accept_ship_days_fig = go.Figure()
        out_of_order_days_fig= go.Figure()
        total_days_fig = go.Figure()

        #create list of empty dataframes
        day_figs = [create_days_fig, confirm_days_fig, accept_days_fig, confirm_ship_days_fig, accept_ship_days_fig, out_of_order_days_fig, total_days_fig]

        #propegate the graphs with grouped dataframe info and turn into scatterplots
        for i in range(len(grouped_df_list)):
            day_figs[i] = px.scatter(grouped_df_list[i], x = 'Time Elapsed (Days)', y = 'Order Count', color = 'Date', hover_name = 'Shipping Details')            
            
            
        #create list of scatterplot titles
        new_title_list = ['Days From Closed Won to Created', 'Days From Created to Confirmed', 'Days From Confirmed to Accepted', 'Days From Confirmed to Shipped', 'Days From Accepted to Shipped', 'Days Out of Stock',
                      'Total Order Time']

        #format the scatterplots
        #iterate through the list of scatterplots
        for i in range(len(day_figs)):
            day_figs[i].update_layout(
                title={
                    'text': f'{new_title_list[i]}<br><sup>Hover over top bar for additional order information</sup>', #add a title
                    'x': 0.5,  #center title
                    'xanchor': 'center',  #center title
                    'yanchor': 'top',  #anchor title to the top
                    'font': {'size': 20},  #main title font size
                },
                title_font_size=24,  #main title font size
                title_font_color="black",  #main title font color
                font=dict(
                    size=12,  #global font size
                    color="black"  #global font color
                ),
                height=600,
            )

        #make the scatterplot point size = 12 for legibility    
        for i in range(len(day_figs)):
            day_figs[i].update_traces(marker=dict(size = 12))    
            
            
        #display the graphs, statistics information and relevant instructions, format text size using previously defined custom_css
        #create a sub-title
        st.markdown('<div class="custom-text-area largest-font">{}</div>'.format('Order Lifetime Graphs'), unsafe_allow_html=True)
        
        #display order lifetime graphs
        st.plotly_chart(hist_list[7], use_container_width=False)
        st.markdown('Select the full screen icon at the top right of the graph for larger view.')
        st.markdown('Select legend icons to select/de-select specific order status changes.')
        st.plotly_chart(box_list[7], use_container_width=False)
        st.markdown('Select the full screen icon at the top right of the graph for larger view.')
        st.markdown('Select legend icons to select/de-select specific order status changes.')
        
        #display detailed order lifetime graphs
        st.plotly_chart(hist_list[8], use_container_width=False)
        st.markdown('Select the full screen icon at the top right of the graph for larger view.')
        st.markdown('Select legend icons to select/de-select specific order status changes.')
        st.plotly_chart(box_list[8], use_container_width=False)
        st.markdown('Select the full screen icon at the top right of the graph for larger view.')
        st.markdown('Select legend icons to select/de-select specific order status changes.')
        
        #create subtitle indicating graphs are status specific
        st.markdown('<div class="custom-text-area largest-font">{}</div>'.format('Status Specific Order Timeline Visualizations'), unsafe_allow_html=True)
        
        #display total time graphs first
        st.plotly_chart(hist_list[6], use_container_width=False)
        st.markdown('Select the full screen icon at the top right of the graph for larger view.')
        st.markdown('Select legend icons to select/de-select specific months.')
        st.plotly_chart(day_figs[6], use_container_width=False)
        st.markdown('Select the full screen icon at the top right of the graph for larger view.')
        st.markdown('Select legend icons to select/de-select specific months.')
        st.plotly_chart(box_list[6], use_container_width=False)
        st.markdown('Select the full screen icon at the top right of the graph for larger view.')
        st.markdown('Select legend icons to select/de-select specific months.')
        #display the total time statistics, create a title for the stats
        st.markdown('<div class="custom-text-area larger-font">{}</div>'.format(f'{title_list[6]} Statistics'), unsafe_allow_html=True)
        st.markdown(output_list[6])
        
        
        #iterate through the remaining graphs to display
        for i in range(6):
            st.plotly_chart(hist_list[i], use_container_width=False)
            st.markdown('Select the full screen icon at the top right of the graph for larger view.')
            st.markdown('Select legend icons to select/de-select specific months.')
            st.plotly_chart(day_figs[i], use_container_width=False)
            st.markdown('Select the full screen icon at the top right of the graph for larger view.')
            st.markdown('Select legend icons to select/de-select specific months.')
            st.plotly_chart(box_list[i], use_container_width=False)
            st.markdown('Select the full screen icon at the top right of the graph for larger view.')
            st.markdown('Select legend icons to select/de-select specific months.')
            st.markdown('<div class="custom-text-area larger-font">{}</div>'.format(f'{title_list[i]} Statistics'), unsafe_allow_html=True)
            st.markdown(output_list[i])
            
#document how to use the supply chain application to the user
st.markdown('<div class="custom-text-area largest-font">{}</div>'.format('User Guide'), unsafe_allow_html=True)

st.markdown('''This application creates interactive visualizations and returns information related to supply chain SLAs. Uploading a sales report document and a supply chain report document is required for the application to process. Once you upload both documents, processing will begin. 

Select the full screen button in the top right to view the graphs full screen. Select specific sections of the graph to zoom in and reset axis to return to normal graph view. Select legend icons to select/de-select values for a more/less detailed view. Please note that when there is a large number of shipping reference numbers the x-axis may not be able to display all reference numbers. Scroll over the bars or the tic-marks at the top of the graph to confirm the shipping reference number. 

The graphs are interactive. Have fun with the visualizations and experiment viewing the data in a variety of ways to find the display that works best for you.''')

st.markdown('<div class="custom-text-area larger-font">{}</div>'.format('Input Document Requirements'), unsafe_allow_html=True)

st.markdown('''
- Ensure you upload the documents to the correct file uploader box. The supply chain report is uploaded to the first file uploader and the sales report is uploaded to the second file uploader.
- The sales uploaded document must contain the following rows: Opportunity Name, Account Name, 18 Char ID, Closed won date, Opportunity Type, and Asset Type.
- The supply chain uploaded document must contain the following columns: Edited By, Field / Event, Old Value, New Value, Edit Date, and Shipping Details: Ref No.''')