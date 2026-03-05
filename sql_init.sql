-- Create core tables for advanced astrological modules

-- 1. profiles: basic user data and natal info
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    first_name TEXT,
    last_name TEXT,
    birth_date DATE,
    birth_time TIME,
    birth_lat DOUBLE PRECISION,
    birth_lon DOUBLE PRECISION,
    is_premium BOOLEAN DEFAULT FALSE
);

-- 2. cosmic_blueprint: psychological natal chart interpretation (Sol, Luna, Asc, Quirón, etc.)
CREATE TABLE IF NOT EXISTS public.cosmic_blueprint (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    sign_sun TEXT,
    sign_moon TEXT,
    sign_ascendant TEXT,
    sign_chiron TEXT,
    interpretation_sun TEXT,
    interpretation_moon TEXT,
    interpretation_ascendant TEXT,
    interpretation_chiron TEXT,
    is_generated_by_ai BOOLEAN DEFAULT FALSE
);

-- 3. transit_events: stores dynamic scores and windows (Módulo 16 / Scoring)
CREATE TABLE IF NOT EXISTS public.transit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    event_date DATE NOT NULL,
    event_type TEXT NOT NULL, -- Ej: 'Júpiter Trígono Sol'
    confidence_score INTEGER,
    insight_text TEXT,
    goal_category TEXT -- 'business', 'love', 'health'
);

-- 4. synastry_insights: stores 100x100 matrix compatibility
CREATE TABLE IF NOT EXISTS public.synastry_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id_1 UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    profile_id_2 UUID REFERENCES public.profiles(id) ON DELETE CASCADE, -- Could be another profile or a target
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    total_score INTEGER,
    love_score INTEGER,
    friction_score INTEGER,
    matrix_data JSONB, -- The raw compatibility matrix
    synthesis_text TEXT
);

-- Set up Row Level Security (RLS) policies
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cosmic_blueprint ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.synastry_insights ENABLE ROW LEVEL SECURITY;

-- Basic Policies (Users can read/write their own data)
CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can view own blueprint" ON public.cosmic_blueprint FOR SELECT USING (auth.uid() = profile_id);
CREATE POLICY "Users can update own blueprint" ON public.cosmic_blueprint FOR ALL USING (auth.uid() = profile_id);

CREATE POLICY "Users can view own transits" ON public.transit_events FOR SELECT USING (auth.uid() = profile_id);
CREATE POLICY "Users can update own transits" ON public.transit_events FOR ALL USING (auth.uid() = profile_id);

CREATE POLICY "Users can view own synastry" ON public.synastry_insights FOR SELECT USING (auth.uid() = profile_id_1 OR auth.uid() = profile_id_2);
CREATE POLICY "Users can update own synastry" ON public.synastry_insights FOR ALL USING (auth.uid() = profile_id_1 OR auth.uid() = profile_id_2);
