
-- Sub-question 1
CREATE VIEW most_active_listing_organizations AS (
	SELECT organization.organization_id, organization.organization, COUNT(listing_id) as total_listings
	FROM fact_table_listings listings
	LEFT JOIN dim_table_organization organization
		ON listings.organization_id = organization.organization_id
	GROUP BY organization.organization_id, organization.organization 
	ORDER BY total_listings DESC
	LIMIT 3
)

-- Sub-question 2
CREATE VIEW organizations_top_job_categories AS (
	WITH top_3_organization_listings AS (
		SELECT organization, job.job_category, COUNT(listing_id) as total_listings
		FROM fact_table_listings listings
		LEFT JOIN dim_table_organization organization
			ON listings.organization_id = organization.organization_id
		LEFT JOIN dim_table_job_category job
			ON listings.job_category_id = job.job_category_id
		WHERE organization.organization_id IN (SELECT organization_id FROM most_active_listing_organizations)
		GROUP BY organization, job.job_category
		ORDER BY organization, total_listings DESC
	), ranked_table AS (
		SELECT *, DENSE_RANK() OVER(PARTITION BY organization ORDER BY total_listings DESC) as ranking
		FROM top_3_organization_listings
	)
	SELECT * 
	FROM ranked_table
	WHERE ranking IN (1, 2, 3)
)

-- Sub-question 3
CREATE VIEW top_9_job_categories_overall AS(
	SELECT job.job_category, COUNT(listings.listing_id) as total_listings
	FROM fact_table_listings listings
	LEFT JOIN dim_table_job_category job
		ON listings.job_category_id = job.job_category_id
	GROUP BY job.job_category
	ORDER BY total_listings DESC
	LIMIT 9
)


-- Helper view to display in powerBI
CREATE VIEW top_3_organizations_percentages AS (
    SELECT organization, total_listings, ROUND(total_listings::numeric / (SELECT COUNT(*) FROM fact_table_listings), 1) AS pct_of_all_listings
    FROM most_active_listing_organizations
)

-- Helper view to display in powerBI
CREATE VIEW top_9_job_categories_percentages AS (
    SELECT job_category, total_listings,
           ROUND(total_listings::numeric / (SELECT COUNT(*) FROM fact_table_listings) * 100, 1) AS pct_of_all_listings
    FROM top_9_job_categories_overall
)

