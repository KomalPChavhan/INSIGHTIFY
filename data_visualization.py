import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import pymysql
from datetime import datetime

# MySQL Database connection details
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "komal**27",
    "database": "atliq_tshirts"
}

# Function to load data from MySQL
@st.cache_data
def load_data(query):
    try:
        conn = pymysql.connect(**db_config)
        df = pd.read_sql_query(query, conn)
        conn.close()

        # Clean and validate the data
        df = df.dropna()  # Drop rows with missing values
        df.columns = df.columns.str.strip().str.lower()  # Normalize column names
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Queries
tshirt_query = "SELECT * FROM t_shirts;"
discount_query = "SELECT * FROM discounts;"
sales_query = "SELECT * FROM sales;"

# Title
st.title("Retail Insights Dashboard 📊")

# Load Data
tshirt_data = load_data(tshirt_query)
discount_data = load_data(discount_query)
sales_data = load_data(sales_query)

# Check if data is loaded correctly
if tshirt_data.empty or sales_data.empty:
    st.error("Data failed to load! Please check your database connection or dataset.")
    st.stop()  # Stop execution if critical data is missing

# Add a dropdown menu for visualization options
st.sidebar.title("Visualization Selector")
visualization_option = st.sidebar.selectbox(
    "Choose a visualization to display",
    [
        "T-Shirts Low in Stock",
        "Stock Quantity by Brand and Color",
        "Sales Trends",
        "Revenue by Category",
        "Most Selling Categories",
        "Most Selling Brands",
        "Sales by Year"
    ]
)

# Conditional rendering of visualizations based on selection
if visualization_option == "T-Shirts Low in Stock":
    st.subheader("T-Shirts Low in Stock 📦")
    stock_threshold = 20
    low_stock = tshirt_data[tshirt_data["stock_quantity"] < stock_threshold]
    
    
    if low_stock.empty:
        st.success("No T-Shirts are running low on stock!")
    else:
        st.dataframe(low_stock)

elif visualization_option == "Stock Quantity by Brand and Color":
    st.subheader("Stock Quantity by Brand and Color 📊")
    fig_stock = px.bar(
        tshirt_data,
        x="brand",
        y="stock_quantity",
        color="color",
    )
    st.plotly_chart(fig_stock)

elif visualization_option == "Sales Trends":
    st.subheader("Sales Trends 📈")
    try:
        # Convert sale_date to datetime
        sales_data['sale_date'] = pd.to_datetime(sales_data['sale_date'], errors='coerce')
        sales_data = sales_data.dropna(subset=['sale_date'])  # Drop invalid dates

        # Add Month column
        sales_data['month'] = sales_data['sale_date'].dt.strftime('%Y-%m')

        # Monthly Sales
        monthly_sales = sales_data.groupby("month")["total_sales"].sum().reset_index()
        fig_monthly_sales = px.line(
            monthly_sales,
            x="month",
            y="total_sales",
            title="Monthly Sales Trend"
        )
        st.plotly_chart(fig_monthly_sales)
    except Exception as e:
        st.error(f"Error processing sales trends: {e}")

elif visualization_option == "Revenue by Category":
    st.subheader("Revenue by Category 💰")
    try:
        revenue_by_category = sales_data.groupby(["brand", "color"])["total_sales"].sum().reset_index()
        fig_revenue = px.bar(
            revenue_by_category,
            x="brand",
            y="total_sales",
            color="color",
            title="Revenue by Brand and Color"
        )
        st.plotly_chart(fig_revenue)
    except Exception as e:
        st.error(f"Error processing revenue data: {e}")

elif visualization_option == "Most Selling Categories":
    st.subheader("Most Selling Categories 🏆")
    try:
        most_sold = sales_data.groupby(["brand", "size"])["quantity_sold"].sum().reset_index()
        fig_best_sellers = px.treemap(
            most_sold,
            path=["brand", "size"],
            values="quantity_sold",
            title="Most Selling Categories"
        )
        st.plotly_chart(fig_best_sellers)
    except Exception as e:
        st.error(f"Error processing most selling categories: {e}")

elif visualization_option == "Most Selling Brands":
    st.subheader("Most Selling Brands 🏅")
    try:
        most_selling_brands = sales_data.groupby("brand")["quantity_sold"].sum().reset_index()
        most_selling_brands = most_selling_brands.sort_values(by="quantity_sold", ascending=False)

        fig_most_selling_brands = px.bar(
            most_selling_brands,
            x="brand",
            y="quantity_sold",
            title="Most Selling Brands",
            labels={"quantity_sold": "Quantity Sold", "brand": "Brand"},
            color="quantity_sold",  # Color the bars based on quantity sold
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig_most_selling_brands)
    except Exception as e:
        st.error(f"Error processing most selling brands data: {e}")

elif visualization_option == "Sales by Year":
    st.subheader("Sales by Year 📅")
     # Convert sale_date to datetime
    sales_data['sale_date'] = pd.to_datetime(sales_data['sale_date'], errors='coerce')
    sales_data = sales_data.dropna(subset=['sale_date'])  # Drop invalid dates

     # Add Month column
    sales_data['month'] = sales_data['sale_date'].dt.strftime('%Y-%m')
    
    available_years = sales_data['sale_date'].dt.year.unique()
    selected_year = st.selectbox("Select Year", available_years)

    # Filter sales data for the selected year
    sales_data_year = sales_data[sales_data['sale_date'].dt.year == selected_year]

    # Visualize sales data for the selected year
    yearly_sales = sales_data_year.groupby("month")["total_sales"].sum().reset_index()
    fig_yearly_sales = px.line(
        yearly_sales,
        x="month",
        y="total_sales",
        title=f"Sales Trend for {selected_year}",
        labels={"total_sales": "Total Sales", "month": "Month"}
    )
    st.plotly_chart(fig_yearly_sales)
