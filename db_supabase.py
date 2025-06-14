def add_prospect_research(**kwargs):
    supabase = init_connection()
    try:
        data_to_insert = {
            "company_name": kwargs.get("company_name"),
            "website": kwargs.get("website"),
            "industry": kwargs.get("industry"),
            "founded_year": kwargs.get("founded_year"),
            "company_size": kwargs.get("company_size"),
            "revenue": kwargs.get("revenue"),
            "location": kwargs.get("location"),
            "contact_name": kwargs.get("contact_name"),
            "contact_title": kwargs.get("contact_title"),
            "contact_email": kwargs.get("contact_email"),
            "linkedin_url": kwargs.get("linkedin_url"),
            "phone": kwargs.get("phone"),
            "keywords": kwargs.get("keywords", []),
            "technology_used": kwargs.get("technology_used", []),
            "notes": kwargs.get("notes"),
            "next_step": kwargs.get("next_step"),
            "next_step_date": kwargs.get("next_step_date"),
            "status": kwargs.get("status", "baru"),
            "source": kwargs.get("source", "manual"),
            "decision_maker": kwargs.get("decision_maker", False),
            "email_status": kwargs.get("email_status"),
            "marketer_id": kwargs.get("marketer_id"),
            "marketer_username": kwargs.get("marketer_username")
        }

        response = supabase.from_("prospect_research").insert(data_to_insert).execute()
        return True, "Prospek berhasil disimpan!"
    except Exception as e:
        return False, f"Gagal menyimpan prospek: {e}"


def edit_prospect_research(prospect_id, **kwargs):
    supabase = init_connection()
    try:
        data_to_update = {
            "company_name": kwargs.get("company_name"),
            "website": kwargs.get("website"),
            "industry": kwargs.get("industry"),
            "founded_year": kwargs.get("founded_year"),
            "company_size": kwargs.get("company_size"),
            "revenue": kwargs.get("revenue"),
            "location": kwargs.get("location"),
            "contact_name": kwargs.get("contact_name"),
            "contact_title": kwargs.get("contact_title"),
            "contact_email": kwargs.get("contact_email"),
            "linkedin_url": kwargs.get("linkedin_url"),
            "phone": kwargs.get("phone"),
            "keywords": kwargs.get("keywords", []),
            "technology_used": kwargs.get("technology_used", []),
            "notes": kwargs.get("notes"),
            "next_step": kwargs.get("next_step"),
            "next_step_date": kwargs.get("next_step_date"),
            "status": kwargs.get("status"),
            "source": kwargs.get("source"),
            "decision_maker": kwargs.get("decision_maker", False),
            "email_status": kwargs.get("email_status")
        }

        response = supabase.from_("prospect_research").update(data_to_update).eq("id", prospect_id).execute()
        return True, "Prospek berhasil diperbarui."
    except Exception as e:
        return False, f"Gagal memperbarui prospek: {e}"


def get_all_prospect_research():
    supabase = init_connection()
    try:
        response = supabase.from_("prospect_research").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data prospek: {e}")
        return []


def get_prospect_research_by_marketer(marketer_id):
    supabase = init_connection()
    try:
        response = supabase.from_("prospect_research").select("*").eq("marketer_id", marketer_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data prospek: {e}")
        return []


def get_prospect_by_id(prospect_id):
    supabase = init_connection()
    try:
        response = supabase.from_("prospect_research").select("*").eq("id", prospect_id).single().execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil detail prospek: {e}")
        return None


def search_prospect_research(keyword):
    supabase = init_connection()
    try:
        response = supabase.from_("prospect_research").select("*").or_(
            f"company_name.ilike.%{keyword}%,"
            f"contact_name.ilike.%{keyword}%,"
            f"industry.ilike.%{keyword}%," 
            f"location.ilike.%{keyword}%"
        ).execute()
        return response.data
    except Exception as e:
        st.error(f"Error saat mencari prospek: {e}")
        return []