import psycopg2
import psycopg2.extras # Import the extras module
from config import load_config
from connect import connect
import time

# A simple function to encode an integer ID into a short string (Base62)
def id_to_short_url(n):
    """Encodes a positive integer into a short Base62 string."""
    if n == 0:
        return '0'
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    base = len(alphabet)
    s = ""

    while n > 0:
        s += alphabet[n % base]
        n //= base
    return s[::-1] # Reverse the string

def create_bulk_short_urls(original_urls):
    """
    Inserts a large batch of URLs, generates short URLs,
    and updates the records efficiently.
    """
    
    # SQL for bulk insert. Note the placeholder is just %s.
    # execute_values will format the data correctly.
    sql_insert = "INSERT INTO url_shortener (original_url) VALUES %s RETURNING id;"
    
    # SQL for bulk update. This is a standard pattern for bulk updates in PostgreSQL.
    sql_update = """
        UPDATE url_shortener SET short_url = data.short_url
        FROM (VALUES %s) AS data (id, short_url)
        WHERE url_shortener.id = data.id;
    """

    config = load_config()
    start_time = time.time()

    try:
        with connect(config) as conn:
            with conn.cursor() as cur:
                
                # === Step 1: Bulk INSERT and get all new IDs ===
                
                # Prepare data for insert: a list of tuples
                # The comma is important to make it a tuple: (url,)
                insert_data = [(url,) for url in original_urls]
                
                print(f"Inserting {len(insert_data)} records...")
                returned_ids = psycopg2.extras.execute_values(
                    cur,
                    sql_insert,
                    insert_data,
                    template=None,
                    fetch=True,     # Fetch the generated IDs and stores them in returned_ids
                    page_size=10000 # Adjust page_size based on memory/performance
                )

                insert_end_time = time.time()
                print(f"Successfully inserted in {insert_end_time - start_time:.2f} seconds. Received {len(returned_ids)} new IDs.")

                # === Step 2: Generate short URLs and prepare data for update ===
                
                # Create a list of tuples for the update: (id, short_url)
                update_data = []
                for row in returned_ids:
                    new_id = row[0]
                    short_url = id_to_short_url(new_id)
                    update_data.append((new_id, short_url))

                # === Step 3: Bulk UPDATE all records ===
                print(f"Updating {len(update_data)} records with short URLs...")
                psycopg2.extras.execute_values(
                    cur,
                    sql_update,
                    update_data,
                    template=None,
                    page_size=10000
                )

                update_end_time = time.time()
                print(f"Successfully updated records in {update_end_time - insert_end_time:.2f} seconds.")

            # The transaction is committed automatically when the 'with conn' block exits
            print("Transaction committed.")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Database error: {error}")
        # The transaction is rolled back automatically on error
        return
        
    end_time = time.time()
    print(f"\nProcessed {len(original_urls)} records in {end_time - start_time:.2f} seconds.")


def update_visit_counts_in_batches(start_id=1, end_id=10000000, batch_size=1000000):
    """
    Updates visit counts for URL records in batches to avoid memory issues
    and provide progress tracking.
    """
    
    # The complex visit count update query
    sql_update = """
        UPDATE url_shortener 
        SET visit_count = 
            GREATEST(0, 
                CASE 
                    WHEN created_at >= now() - interval '1 day' THEN
                        floor(exp(random() * 3))::int
                    WHEN created_at >= now() - interval '7 days' THEN
                        floor(exp(random() * 5))::int
                    WHEN created_at >= now() - interval '30 days' THEN
                        floor(exp(random() * 7))::int
                    WHEN created_at >= now() - interval '365 days' THEN
                        floor(exp(random() * 9))::int
                    ELSE
                        floor(exp(random() * 11))::int
                END
                * CASE 
                    WHEN original_url ILIKE '%%youtube%%' OR original_url ILIKE '%%tiktok%%' THEN
                        1 + floor(random() * 20)
                    WHEN original_url ILIKE '%%twitter%%' OR original_url ILIKE '%%instagram%%' OR original_url ILIKE '%%reddit%%' THEN
                        1 + floor(random() * 15)
                    WHEN original_url ILIKE '%%github%%' OR original_url ILIKE '%%stackoverflow%%' THEN
                        1 + floor(random() * 8)
                    WHEN original_url ILIKE '%%news%%' OR original_url ILIKE '%%medium%%' THEN
                        1 + floor(random() * 12)
                    ELSE
                        1 + floor(random() * 5)
                END
                * CASE 
                    WHEN random() < 0.001 THEN floor(random() * 1000) + 100
                    WHEN random() < 0.01 THEN floor(random() * 100) + 10
                    WHEN random() < 0.05 THEN floor(random() * 10) + 2
                    ELSE 1
                END
            )
        WHERE id >= %s AND id < %s;
    """

    config = load_config()
    total_records = end_id - start_id + 1
    total_batches = (total_records + batch_size - 1) // batch_size  # Ceiling division
    
    print(f"Starting visit count update for {total_records:,} records ({start_id} to {end_id})")
    print(f"Processing in {total_batches} batches of {batch_size:,} records each\n")
    
    overall_start_time = time.time()
    
    try:
        with connect(config) as conn:
            with conn.cursor() as cur:
                
                for batch_num in range(total_batches):
                    batch_start_id = start_id + (batch_num * batch_size)
                    batch_end_id = min(batch_start_id + batch_size, end_id + 1)
                    
                    print(f"Batch {batch_num + 1}/{total_batches}: Updating IDs {batch_start_id:,} to {batch_end_id - 1:,}")
                    
                    batch_start_time = time.time()
                    

                    # Debug: print SQL and parameters

                    print("  [DEBUG] Executing SQL:")
                    print(sql_update)
                    print(f"  [DEBUG] Parameters: batch_start_id={batch_start_id}, batch_end_id={batch_end_id}")
                    print(f"  [DEBUG] Number of %s in SQL: {sql_update.count('%s')}")

                    # IMPORTANT: Use only cur.execute for this UPDATE!
                    # Do NOT use execute_values or executemany here.
                    rows_affected = 0
                    try:
                        cur.execute(sql_update, (batch_start_id, batch_end_id))
                        rows_affected = cur.rowcount
                    except Exception as e:
                        print(f"  [ERROR] Failed to execute batch update: {e}")
                        raise
                    
                    batch_end_time = time.time()
                    batch_duration = batch_end_time - batch_start_time
                    
                    print(f"  ✓ Updated {rows_affected:,} records in {batch_duration:.2f} seconds")
                    
                    # Commit after each batch to avoid long-running transactions
                    conn.commit()
                    
                    # Calculate and show progress
                    progress = ((batch_num + 1) / total_batches) * 100
                    elapsed_time = batch_end_time - overall_start_time
                    estimated_total_time = elapsed_time / (progress / 100) if progress > 0 else 0
                    estimated_remaining = estimated_total_time - elapsed_time
                    
                    print(f"  Progress: {progress:.1f}% | Elapsed: {elapsed_time:.1f}s | Est. remaining: {estimated_remaining:.1f}s\n")

            print("All batches completed successfully!")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Database error during batch update: {error}")
        return False
        
    overall_end_time = time.time()
    total_duration = overall_end_time - overall_start_time
    print(f"\nCompleted visit count update for {total_records:,} records in {total_duration:.2f} seconds.")
    print(f"Average: {total_duration/total_batches:.2f} seconds per batch")
    
    return True


if __name__ == '__main__':
    # --- Update visit counts for existing records in batches ---
    print("Starting batch update of visit counts for IDs 1 to 10,000,000...")
    
    # Run the batch update function
    success = update_visit_counts_in_batches(
        start_id=1,
        end_id=10000000,
        batch_size=1000000
    )
    
    if success:
        print("✓ Batch update completed successfully!")
    else:
        print("✗ Batch update failed!")
    
    # Uncomment the lines below if you want to also generate new URLs
    # print("\nGenerating 10,000,000 dummy URLs for the bulk test...")
    # urls_to_add = [f"https://www.some-website.com/page/item_{i}" for i in range(10000000)]
    # create_bulk_short_urls(urls_to_add)
