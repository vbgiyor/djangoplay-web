# Constants for user-related models in the Django application

# Member status codes to track external contact (non-authenticated) user statuses
MEMBER_STATUS_CODES = {
    'PEND': 'Pending',    # Awaiting verification or approval
    'ACTV': 'Active',     # Fully active member with platform access
    'SUSP': 'Suspended',  # Temporarily inactive
    'TERM': 'Terminated'  # Permanently removed from platform
}

# Employment status codes to track employment statuses
EMPLOYMENT_STATUS_CODES = {
    'ACTV': 'Active',      # Currently employed and active
    'LEAV': 'On Leave',    # On approved leave
    'TERM': 'Terminated',  # Employment ended
    'RETD': 'Retired',     # Retired from employment
    'PEND': 'Pending'     # Awaiting verification or approval
}

# Role codes to define user roles with associated permissions
ROLE_CODES = {
    'CEO': 'Chief Executive Officer',            # Top executive with full access
    'DJGO': 'Django Superuser',                  # System superuser with full access
    'CFO': 'Chief Financial Officer',            # Senior finance executive
    'FMGR': 'Finance Manager',                   # Manages finance department
    'AMGR': 'Accounts Payable Manager',          # Manages AP team
    'ASPC': 'Accounts Payable Specialist',       # AP team member
    'RMGR': 'Accounts Receivable Manager',       # Manages AR team
    'RSPC': 'Accounts Receivable Specialist',    # AR team member
    'ADIR': 'Audit Director',                    # Leads audit team
    'AUDT': 'Auditor',                           # Audit team member
    'TDIR': 'Tax Director',                      # Leads tax team
    'TAX': 'Tax Analyst',                       # Tax team member
    'RDIR': 'Risk Director',                     # Leads risk management
    'RISK': 'Risk Analyst',                      # Risk team member
    'IDIR': 'Investment Director',               # Leads investment team
    'INV': 'Investment Analyst',                 # Investment team member
    'CDIR': 'Compliance Director',               # Leads compliance
    'COFF': 'Compliance Officer',                # Compliance team member
    'TMGR': 'Trading Manager',                   # Manages trading team
    'TRAD': 'Trader',                            # Trading team member
    'CFDR': 'Corporate Finance Director',        # Leads corporate finance
    'CFAN': 'Corporate Finance Analyst',         # Corporate finance team member
    'YMGR': 'Treasury Manager',                  # Manages treasury
    'TRY': 'Treasury Analyst',                   # Treasury team member
    'PMGR': 'Reporting Manager',                 # Manages financial reporting
    'RPT': 'Reporting Analyst',                  # Reporting team member
    'CMGR': 'Credit Manager',                    # Manages credit team
    'CRD': 'Credit Analyst',                     # Credit team member
    'MDIR': 'M&A Director',                      # Leads M&A team
    'MNA': 'M&A Analyst',                        # M&A team member
    'SYS': 'System User',                        # System-created user with mixed read/write access
    'SSO': 'Social User'                         # Social platform user with read-only access
}

# Department codes to categorize employees and members
DEPARTMENT_CODES = {
    'FIN': 'Finance',                    # General finance department
    'AP': 'Accounts Payable',            # Accounts payable department
    'AR': 'Accounts Receivable',         # Accounts receivable department
    'AUD': 'Audit',                      # Audit department
    'TAX': 'Tax',                        # Tax department
    'RSK': 'Risk Management',            # Risk management department
    'INV': 'Investment',                 # Investment department
    'COM': 'Compliance',                 # Compliance department
    'TRD': 'Trading',                    # Trading department
    'COR': 'Corporate Finance',          # Corporate finance department
    'TRY': 'Treasury',                   # Treasury department
    'RPT': 'Financial Reporting',        # Financial reporting department
    'CRD': 'Credit',                     # Credit department
    'MNA': 'Mergers & Acquisitions',     # M&A department
    'SSO': 'Social Platform',            # Department for social platform users
    'DIR': 'Board of Directors'          # Department for leadership
}

# Employee type codes to classify employee categories
EMPLOYEE_TYPE_CODES = {
    'FT': 'Full-Time',        # Full-time system employee
    'PT': 'Part-Time',        # Part-time system employee
    'CTR': 'Contractor',      # Contract-based employee
    'INT': 'Intern',          # Intern employee
    'SSO': 'Social Platform'  # Social platform user with read-only access
}

# Leave type codes to define leave categories
LEAVE_TYPE_CODES = {
    'ANUL': 'Annual Leave',   # Paid annual leave
    'SICK': 'Sick Leave',     # Medical leave
    'MAT': 'Maternity Leave', # Maternity or paternity leave
    'UNPD': 'Unpaid Leave'    # Unpaid leave
}

# SSO provider codes used for SignUpRequest and Employee models to track authentication methods
SSO_PROVIDER_CODES = {
    'GOOG': 'Google',   # Google SSO
    'APPL': 'Apple',    # Apple SSO
    'EMAIL': 'Email'     # Email-based authentication
}
