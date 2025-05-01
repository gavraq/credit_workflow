# Migration Instructions

To migrate the database and create the LimitType model, follow these steps:

1. Create the migration files for the new models:
```
python manage.py makemigrations
```

2. Apply the migrations to update the database:
```
python manage.py migrate
```

3. Load the initial limit types data:
```
python manage.py load_limit_types
```

4. Restart your development server:
```
python manage.py runserver
```

## Important Notes

### 1. Data Migration
The migration will add a new LimitType model and change the CreditLimit.limit_type field from a CharField to a ForeignKey. 

### 2. Existing Data Handling
If you have existing CreditLimit records, the system will attempt to match them with the newly created LimitType entries based on the original code values.

### 3. Benefits of the New Approach
Using a foreign key relationship to LimitType provides several advantages:
- Better data integrity and consistency
- Ability to add new limit types through the admin interface
- Centralized management of limit type properties
- Easier querying and reporting

### 4. Forms and Wizard Changes
The form wizard has been updated to handle the new relationship and properly store/retrieve limit type data. The changes include:
- Custom JSON serialization for Decimal fields
- Improved form validation
- Better handling of form submissions
