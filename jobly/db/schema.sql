-- Enable the pgvector extension to work with embedding vectors
create extension if not exists vector;

-- Drop table if exists to ensure clean slate for new schema
drop table if exists public.job_postings;

-- Create the job_postings table
create table public.job_postings (
  id uuid not null default gen_random_uuid (),
  
  -- Deduplication fields
  fingerprint text not null, -- Unique hash (e.g., lowercase(company_title))
  
  -- Array fields for merging duplicates
  source_urls text[] not null, -- List of all URLs found for this job
  platforms text[] not null,   -- List of platforms (seek, linkedin, etc.)
  locations text[] not null,   -- List of locations
  
  -- Standard fields
  job_title text not null,
  company text,
  
  -- LLM output stored as flexible JSON
  llm_analysis jsonb,
  
  -- Embedding for semantic search
  embedding vector (1536),
  
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  
  -- Additional fields
  description text,
  seniority text,
  salary text,
  posted_at date,
  closing_date date,
  
  constraint job_postings_pkey primary key (id),
  constraint job_postings_fingerprint_key unique (fingerprint)
);

-- Create an index on the JSONB column
create index idx_job_postings_llm_analysis on public.job_postings using gin (llm_analysis);

-- Comment on table and columns
comment on table public.job_postings is 'Stores job descriptions and LLM-extracted insights. Handles deduplication via fingerprint.';
comment on column public.job_postings.fingerprint is 'Unique identifier derived from Company + Title to detect duplicates.';
