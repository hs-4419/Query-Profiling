create database backend;

\c backend

create table url_shortener(
	id serial primary key,
	original_url text,
	short_code varchar(6) unique,
	created_at timestamptz default now()
);

-- Pre requisite: Adding 10M random records to the table

    -- Create helper function for random strings
CREATE OR REPLACE FUNCTION random_string(length INTEGER) 
RETURNS TEXT AS $$
BEGIN
    RETURN array_to_string(
        ARRAY(
            SELECT chr(
                CASE 
                    WHEN random() < 0.3 THEN 97 + floor(random() * 26)::int   -- a-z
                    WHEN random() < 0.6 THEN 65 + floor(random() * 26)::int   -- A-Z
                    ELSE 48 + floor(random() * 10)::int                       -- 0-9
                END
            )
            FROM generate_series(1, length)
        ), 
        ''
    );
END;
$$ LANGUAGE plpgsql;

    -- Insert with maximum randomness
INSERT INTO url_shortener(original_url, short_code, created_at)
SELECT 
    -- Super diverse URL patterns
    CASE floor(random() * 50)
        WHEN 0 THEN 'https://google.com/search?q=' || replace(random_string(20), ' ', '+')
        WHEN 1 THEN 'https://youtube.com/watch?v=' || random_string(11)
        WHEN 2 THEN 'https://facebook.com/' || random_string(15) || '/posts/' || floor(random() * 999999999)::text
        WHEN 3 THEN 'https://twitter.com/' || random_string(12) || '/status/' || floor(random() * 9999999999)::text
        WHEN 4 THEN 'https://instagram.com/p/' || random_string(11) || '/'
        WHEN 5 THEN 'https://linkedin.com/in/' || random_string(15)
        WHEN 6 THEN 'https://github.com/' || random_string(12) || '/' || random_string(15)
        WHEN 7 THEN 'https://stackoverflow.com/questions/' || floor(random() * 100000000)::text || '/' || replace(random_string(30), ' ', '-')
        WHEN 8 THEN 'https://reddit.com/r/' || random_string(15) || '/comments/' || random_string(6)
        WHEN 9 THEN 'https://amazon.com/dp/' || random_string(10) || '?tag=' || random_string(8)
        WHEN 10 THEN 'https://ebay.com/itm/' || floor(random() * 999999999999)::text
        WHEN 11 THEN 'https://netflix.com/title/' || floor(random() * 99999999)::text
        WHEN 12 THEN 'https://spotify.com/track/' || random_string(22)
        WHEN 13 THEN 'https://medium.com/@' || random_string(12) || '/' || replace(random_string(25), ' ', '-')
        WHEN 14 THEN 'https://discord.gg/' || random_string(8)
        WHEN 15 THEN 'https://twitch.tv/' || random_string(12)
        WHEN 16 THEN 'https://pinterest.com/pin/' || floor(random() * 999999999999999)::text
        WHEN 17 THEN 'https://tiktok.com/@' || random_string(15) || '/video/' || floor(random() * 999999999999999)::text
        WHEN 18 THEN 'https://news.ycombinator.com/item?id=' || floor(random() * 50000000)::text
        WHEN 19 THEN 'https://stripe.com/docs/' || replace(random_string(20), ' ', '-')
        WHEN 20 THEN 'https://docs.aws.amazon.com/' || replace(random_string(25), ' ', '/')
        WHEN 21 THEN 'https://firebase.google.com/docs/' || replace(random_string(15), ' ', '/')
        WHEN 22 THEN 'https://developer.mozilla.org/en-US/docs/' || replace(random_string(20), ' ', '/')
        WHEN 23 THEN 'https://api.github.com/repos/' || random_string(15) || '/' || random_string(20)
        WHEN 24 THEN 'https://www.npmjs.com/package/' || replace(random_string(15), ' ', '-')
        WHEN 25 THEN 'https://pypi.org/project/' || replace(random_string(12), ' ', '-') || '/'
        WHEN 26 THEN 'https://hub.docker.com/r/' || random_string(10) || '/' || random_string(15)
        WHEN 27 THEN 'https://marketplace.visualstudio.com/items?itemName=' || random_string(20)
        WHEN 28 THEN 'https://play.google.com/store/apps/details?id=' || random_string(25)
        WHEN 29 THEN 'https://apps.apple.com/app/id' || floor(random() * 999999999)::text
        ELSE 'https://' || random_string(15) || '.com/' || replace(random_string(30), ' ', '/') || '?id=' || random_string(10)
    END,
    
    -- Guaranteed unique short URLs
    random_string(6),
    
    -- Realistic timestamp distribution
    CASE 
        WHEN random() < 0.05 THEN now() - (random() * interval '1 hour')       -- 5% last hour
        WHEN random() < 0.15 THEN now() - (random() * interval '1 day')        -- 10% today
        WHEN random() < 0.35 THEN now() - (random() * interval '7 days')       -- 20% this week
        WHEN random() < 0.55 THEN now() - (random() * interval '30 days')      -- 20% this month
        WHEN random() < 0.75 THEN now() - (random() * interval '90 days')      -- 20% last 3 months
        WHEN random() < 0.90 THEN now() - (random() * interval '365 days')     -- 15% this year
        ELSE now() - (random() * interval '1095 days')                         -- 10% last 3 years
    END

FROM generate_series(1, 10000000) AS i
ON CONFLICT (short_code) DO NOTHING;  -- Handle any duplicate short_codes

    -- Clean up helper function
DROP FUNCTION random_string(INTEGER);

-- 3) Adding visit_count column
ALTER TABLE url_shortener 
ADD COLUMN visit_count INTEGER DEFAULT 0 NOT NULL;

-- Advanced realistic visit count population
UPDATE url_shortener 
SET visit_count = 
    -- Base visits based on age and platform
    GREATEST(0, 
        -- Age factor (older = potentially more visits)
        CASE 
            WHEN created_at >= now() - interval '1 day' THEN
                floor(exp(random() * 3))::int                               -- 1-20 visits (exponential)
            WHEN created_at >= now() - interval '7 days' THEN
                floor(exp(random() * 5))::int                               -- 1-148 visits
            WHEN created_at >= now() - interval '30 days' THEN
                floor(exp(random() * 7))::int                               -- 1-1096 visits
            WHEN created_at >= now() - interval '365 days' THEN
                floor(exp(random() * 9))::int                               -- 1-8103 visits
            ELSE
                floor(exp(random() * 11))::int                              -- 1-59874 visits
        END
        
        -- Platform multiplier (some platforms get shared more)
        * CASE 
            WHEN original_url ILIKE '%youtube%' OR original_url ILIKE '%tiktok%' THEN
                1 + floor(random() * 20)                                    -- 1-20x multiplier for video content
            WHEN original_url ILIKE '%twitter%' OR original_url ILIKE '%instagram%' OR original_url ILIKE '%reddit%' THEN
                1 + floor(random() * 15)                                    -- 1-15x for social media
            WHEN original_url ILIKE '%github%' OR original_url ILIKE '%stackoverflow%' THEN
                1 + floor(random() * 8)                                     -- 1-8x for developer content
            WHEN original_url ILIKE '%news%' OR original_url ILIKE '%medium%' THEN
                1 + floor(random() * 12)                                    -- 1-12x for news/articles
            ELSE
                1 + floor(random() * 5)                                     -- 1-5x for other content
        END
        
        -- Random viral factor (small chance of going viral)
        * CASE 
            WHEN random() < 0.001 THEN floor(random() * 1000) + 100        -- 0.1% chance of 100-1099x multiplier (viral)
            WHEN random() < 0.01 THEN floor(random() * 100) + 10           -- 1% chance of 10-109x multiplier (popular)
            WHEN random() < 0.05 THEN floor(random() * 10) + 2             -- 5% chance of 2-11x multiplier (trending)
            ELSE 1                                                          -- 94% get normal traffic
        END
    );