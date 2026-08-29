import streamlit as st
import pandas as pd
import json
import base64

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Orecraft Mining Tool",
    page_icon="⚒️",
    layout="wide"
)

st.title("⚒️ Orecraft Mining Tool ⚒️")

# ---------------------------------------------------------
# DATA LOADING FROM EXCEL (MATRIX STRUCTURE)
# ---------------------------------------------------------
@st.cache_data
def load_database_from_excel(file_path="orecraft_database.xlsx"):
    df = pd.read_excel(file_path)
    
    # Standardize column names
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    # Identify meta columns and ingredient columns
    meta_cols = ["type", "name", "rarity"]
    ingredient_cols = [c for c in df.columns if c not in meta_cols]
    
    items_order = []
    items_db = {}
    
    bars_order = []
    bars_db = {}
    
    ores_order = []
    ores_db = {}

    types_map = {}
    
    for _, row in df.iterrows():
        row_type = str(row["type"]).strip().lower()
        item_name = str(row["name"]).strip()
        types_map[item_name.lower()] = row_type
        
        # Build recipe dictionary from matrix columns (>0)
        recipe = {}
        for ing_col in ingredient_cols:
            val = row[ing_col]
            if pd.notna(val) and isinstance(val, (int, float)) and val > 0:
                recipe[ing_col] = int(val)
                
        if row_type == "item":
            items_order.append(item_name)
            items_db[item_name] = recipe
            
        elif row_type == "bar":
            bars_order.append(item_name)
            bars_db[item_name] = recipe
            
        elif row_type == "ore":
            ores_order.append(item_name)
            rarity = str(row["rarity"]).strip() if pd.notna(row["rarity"]) else "Unknown"
            ores_db[item_name] = rarity

    # Mapping for case-insensitive lookup
    all_names = list(items_db.keys()) + list(bars_db.keys()) + list(ores_db.keys()) + [c.title() for c in ingredient_cols]
    name_case_map = {k.lower(): k for k in all_names}
    
    return items_order, items_db, bars_order, bars_db, ores_order, ores_db, name_case_map, types_map

# Load database
try:
    ITEMS_ORDER, ITEMS_DB, BARS_ORDER, BARS_DB, ORES_ORDER, ORES_DB, NAME_CASE_MAP, TYPES_MAP = load_database_from_excel()
except Exception as e:
    st.error(f"Error loading the Excel file 'orecraft_database.xlsx': {e}")
    st.stop()

# Helper to format numbers (k / M / B)
def format_num(val, compact=False):
    if not compact or not isinstance(val, (int, float)):
        return str(val) if isinstance(val, (int, float)) else val
    if val >= 1_000_000_000:
        res = f"{val / 1_000_000_000:.1f}".rstrip('0').rstrip('.')
        return f"{res}B"
    elif val >= 1_000_000:
        res = f"{val / 1_000_000:.1f}".rstrip('0').rstrip('.')
        return f"{res}M"
    elif val >= 1_000:
        res = f"{val / 1_000:.1f}".rstrip('0').rstrip('.')
        return f"{res}k"
    return str(val)

# Helper to parse manual text input to numeric values
def parse_compact_input(val_str):
    if isinstance(val_str, (int, float)):
        return int(val_str)
    
    val_str = str(val_str).strip().lower().replace(' ', '')
    if not val_str:
        return 0
    
    multiplier = 1
    if val_str.endswith('b'):
        multiplier = 1_000_000_000
        val_str = val_str[:-1]
    elif val_str.endswith('m'):
        multiplier = 1_000_000
        val_str = val_str[:-1]
    elif val_str.endswith('k'):
        multiplier = 1_000
        val_str = val_str[:-1]
        
    val_str = val_str.replace(',', '.')
    try:
        return int(float(val_str) * multiplier)
    except ValueError:
        return 0

# ---------------------------------------------------------
# CALCULATION ENGINE (CASE-INSENSITIVE & RECURSIVE)
# ---------------------------------------------------------
def get_recipe_dict(name):
    name_lower = name.lower()
    for k, v in ITEMS_DB.items():
        if k.lower() == name_lower:
            return v
    for k, v in BARS_DB.items():
        if k.lower() == name_lower:
            return v
    return {}

def calculate_requirements(target_name, quantity, inventory):
    gross_items = {}
    gross_bars = {}
    gross_ores = {}

    # 1. GROSS CALCULATION (Fully recursive)
    def resolve_gross(name, qty):
        recipe = get_recipe_dict(name)
        for req_raw, req_qty in recipe.items():
            req_name = NAME_CASE_MAP.get(req_raw.lower(), req_raw)
            tot_qty = req_qty * qty
            req_type = TYPES_MAP.get(req_name.lower(), "unknown")

            if req_type == "item":
                gross_items[req_name] = gross_items.get(req_name, 0) + tot_qty
                resolve_gross(req_name, tot_qty)
            elif req_type == "bar":
                gross_bars[req_name] = gross_bars.get(req_name, 0) + tot_qty
                resolve_gross(req_name, tot_qty)
            else:
                gross_ores[req_name] = gross_ores.get(req_name, 0) + tot_qty

    # 2. NET CALCULATION (Top-Down considering existing inventory)
    net_items = {}
    net_bars = {}
    net_ores = {}

    def resolve_net(name, qty_needed):
        recipe = get_recipe_dict(name)
        for req_raw, req_qty in recipe.items():
            req_name = NAME_CASE_MAP.get(req_raw.lower(), req_raw)
            tot_qty = req_qty * qty_needed
            req_type = TYPES_MAP.get(req_name.lower(), "unknown")
            in_stock = inventory.get(req_name, 0)

            if req_type == "item":
                net_items[req_name] = net_items.get(req_name, 0) + tot_qty
                actual_to_craft = max(0, tot_qty - in_stock)
                if actual_to_craft > 0:
                    resolve_net(req_name, actual_to_craft)
            elif req_type == "bar":
                net_bars[req_name] = net_bars.get(req_name, 0) + tot_qty
                actual_to_smelt = max(0, tot_qty - in_stock)
                if actual_to_smelt > 0:
                    resolve_net(req_name, actual_to_smelt)
            else:
                net_ores[req_name] = net_ores.get(req_name, 0) + tot_qty

    resolve_gross(target_name, quantity)
    resolve_net(target_name, quantity)

    return gross_items, gross_bars, gross_ores, net_items, net_bars, net_ores

def sort_by_tier(data_dict, order_list):
    sorted_dict = {}
    for item in order_list:
        matched_key = None
        for k in data_dict.keys():
            if k.lower() == item.lower():
                matched_key = k
                break
        if matched_key:
            sorted_dict[matched_key] = data_dict[matched_key]

    for k, v in data_dict.items():
        if k not in sorted_dict:
            sorted_dict[k] = v
    return sorted_dict

# ---------------------------------------------------------
# PERSISTENT STORAGE MANAGEMENT (URL PARAMETERS)
# ---------------------------------------------------------
DEFAULT_PLACEHOLDER = " Select item or bar..."
HEADER_ITEMS = "📦 --- CRAFTING ITEMS ---"
HEADER_BARS = "🔥 --- BARS ---"

# Load initial state from browser URL params on reload/F5
query_params = st.query_params

if "initialized" not in st.session_state:
    st.session_state.initialized = True
    
    # Restore inventory
    if "data" in query_params:
        try:
            decoded = base64.b64decode(query_params["data"].encode()).decode()
            st.session_state.inventory = json.loads(decoded)
        except Exception:
            st.session_state.inventory = {}
    else:
        st.session_state.inventory = {}

    # Restore item selection
    if "choice" in query_params:
        st.session_state.selected_item_choice = query_params["choice"]
    else:
        st.session_state.selected_item_choice = DEFAULT_PLACEHOLDER

    # Restore quantity
    if "qty" in query_params and query_params["qty"].isdigit():
        st.session_state.selected_item_qty = int(query_params["qty"])
    else:
        st.session_state.selected_item_qty = 1

if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0

def sync_state_to_url():
    """Sync session state into browser URL query parameters."""
    encoded_inv = base64.b64encode(json.dumps(st.session_state.inventory).encode()).decode()
    st.query_params["data"] = encoded_inv
    st.query_params["choice"] = st.session_state.selected_item_choice
    st.query_params["qty"] = str(st.session_state.selected_item_qty)

# ---------------------------------------------------------
# USER INTERFACE / CONTROLS
# ---------------------------------------------------------
st.sidebar.header("🎒 Settings & Inventory")

if st.sidebar.button("🗑️ Reset Inventory", width="stretch"):
    st.session_state.inventory = {}
    st.session_state.reset_counter += 1
    st.session_state.selected_item_choice = DEFAULT_PLACEHOLDER
    st.session_state.selected_item_qty = 1
    st.query_params.clear()
    st.rerun()

compact_view = st.sidebar.toggle(
    "Compact unit display",
    value=False,
    help="Enable to display values like 10,000 as 10k, 1,000,000 as 1M, and 1,000,000,000 as 1B."
)

# Build dropdown options
options_map = {}
display_options = [DEFAULT_PLACEHOLDER, HEADER_ITEMS]

for item in ITEMS_ORDER:
    disp = f"   └─ {item}"
    display_options.append(disp)
    options_map[disp] = item

display_options.append(HEADER_BARS)
for bar in BARS_ORDER:
    disp = f"   └─ {bar}"
    display_options.append(disp)
    options_map[disp] = bar

col_select, col_qty = st.columns([3, 1])

with col_select:
    selected_disp = st.selectbox(
        "Select the Item or Bar to craft:",
        options=display_options,
        key="selected_item_choice",
        on_change=sync_state_to_url
    )

with col_qty:
    item_quantity = st.number_input(
        "Amount to craft:",
        min_value=1,
        step=1,
        key="selected_item_qty",
        on_change=sync_state_to_url
    )

if selected_disp == DEFAULT_PLACEHOLDER:
    st.info("👈 Please select an item or bar at the top to calculate required ingredients.")
    st.stop()

if selected_disp in [HEADER_ITEMS, HEADER_BARS]:
    st.warning("⚠️ You have selected a category header. Please select a specific item or bar below it.")
    st.stop()

selected_option = options_map.get(selected_disp, selected_disp)

# Execute calculation
g_items, g_bars, g_ores, n_items, n_bars, n_ores = calculate_requirements(
    selected_option, 
    item_quantity, 
    st.session_state.inventory
)

# Sort by Tier
g_items = sort_by_tier(g_items, ITEMS_ORDER)
g_bars = sort_by_tier(g_bars, BARS_ORDER)
g_ores = sort_by_tier(g_ores, ORES_ORDER)

st.markdown("---")
st.header(f"Calculation for {item_quantity}x {selected_option}")
st.info("💡 **Tip:** Enter your existing stock for intermediate items or bars; the required ores will automatically adjust!")

cnt = st.session_state.reset_counter

# ---------------------------------------------------------
# INTERACTIVE DATA EDITORS FOR RESULTS
# ---------------------------------------------------------

# 1. ORES
with st.expander("⛏️ Total Ores", expanded=True):
    ores_data = []
    for ore_name, gross_qty in g_ores.items():
        in_stock = st.session_state.inventory.get(ore_name, 0)
        net_from_recipes = n_ores.get(ore_name, 0)
        net_to_mine = max(0, net_from_recipes - in_stock)
        rarity = ORES_DB.get(ore_name, "Unknown")
        
        ores_data.append({
            "Ore Name": ore_name,
            "Gross Needed": format_num(gross_qty, compact_view),
            "In Stock ✏️": format_num(in_stock, compact_view),
            "Net Still to Mine": format_num(net_to_mine, compact_view),
            "Rarity": rarity
        })
    
    if ores_data:
        ores_df = pd.DataFrame(ores_data)
        edited_ores = st.data_editor(
            ores_df,
            column_config={
                "Ore Name": st.column_config.TextColumn(disabled=True),
                "Gross Needed": st.column_config.TextColumn(disabled=True),
                "In Stock ✏️": st.column_config.TextColumn(disabled=False),
                "Net Still to Mine": st.column_config.TextColumn(disabled=True),
                "Rarity": st.column_config.TextColumn(disabled=True),
            },
            hide_index=True,
            width="stretch",
            key=f"editor_ores_{cnt}"
        )
        for _, row in edited_ores.iterrows():
            name = row["Ore Name"]
            parsed_val = parse_compact_input(row["In Stock ✏️"])
            if st.session_state.inventory.get(name, 0) != parsed_val:
                st.session_state.inventory[name] = parsed_val
                sync_state_to_url()
                st.rerun()
    else:
        st.info("No ores required for this selection.")

# 2. BARS
with st.expander("🔥 Total Bars", expanded=True):
    bars_data = []
    for bar_name, gross_qty in g_bars.items():
        in_stock = st.session_state.inventory.get(bar_name, 0)
        net_needed_base = n_bars.get(bar_name, 0)
        net_to_smelt = max(0, net_needed_base - in_stock)
        
        bars_data.append({
            "Bar Name": bar_name,
            "Gross Needed": format_num(gross_qty, compact_view),
            "In Stock ✏️": format_num(in_stock, compact_view),
            "Net Still to Smelt": format_num(net_to_smelt, compact_view)
        })
    
    if bars_data:
        bars_df = pd.DataFrame(bars_data)
        edited_bars = st.data_editor(
            bars_df,
            column_config={
                "Bar Name": st.column_config.TextColumn(disabled=True),
                "Gross Needed": st.column_config.TextColumn(disabled=True),
                "In Stock ✏️": st.column_config.TextColumn(disabled=False),
                "Net Still to Smelt": st.column_config.TextColumn(disabled=True),
            },
            hide_index=True,
            width="stretch",
            key=f"editor_bars_{cnt}"
        )
        for _, row in edited_bars.iterrows():
            name = row["Bar Name"]
            parsed_val = parse_compact_input(row["In Stock ✏️"])
            if st.session_state.inventory.get(name, 0) != parsed_val:
                st.session_state.inventory[name] = parsed_val
                sync_state_to_url()
                st.rerun()
    else:
        st.info("No bars required for this selection.")

# 3. INTERMEDIATE ITEMS / CRAFTING TREE
with st.expander("📦 Intermediate Items (Crafting Tree)", expanded=True):
    items_data = []
    for it_name, gross_qty in g_items.items():
        in_stock = st.session_state.inventory.get(it_name, 0)
        net_needed_base = n_items.get(it_name, 0)
        net_to_craft = max(0, net_needed_base - in_stock)
        
        items_data.append({
            "Item Name": it_name,
            "Gross Needed": format_num(gross_qty, compact_view),
            "In Stock ✏️": format_num(in_stock, compact_view),
            "Net Still to Craft": format_num(net_to_craft, compact_view)
        })
    
    if items_data:
        items_df = pd.DataFrame(items_data)
        edited_items = st.data_editor(
            items_df,
            column_config={
                "Item Name": st.column_config.TextColumn(disabled=True),
                "Gross Needed": st.column_config.TextColumn(disabled=True),
                "In Stock ✏️": st.column_config.TextColumn(disabled=False),
                "Net Still to Craft": st.column_config.TextColumn(disabled=True),
            },
            hide_index=True,
            width="stretch",
            key=f"editor_items_{cnt}"
        )
        for _, row in edited_items.iterrows():
            name = row["Item Name"]
            parsed_val = parse_compact_input(row["In Stock ✏️"])
            if st.session_state.inventory.get(name, 0) != parsed_val:
                st.session_state.inventory[name] = parsed_val
                sync_state_to_url()
                st.rerun()
    else:
        st.info("No intermediate items required for this selection.")