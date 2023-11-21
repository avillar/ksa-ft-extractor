ROOT_FTHEME_IDS = [1130, 1132]

THEME_CHILDREN_QUERY = '''
    select * from t_package where parent_id = $ID$
'''

CLS_QUERY = '''
    select cls.Object_ID as object_id, coalesce(cls.Alias, cls.Name) as label,
           cls.Name as name, cls.Note as description,
           pkg.Package_ID as pkg_id, pkg.Name as pkg_name,
           scls.Object_ID as super_object_id, scls.Name as super_name
    from t_object cls
    join t_package pkg on (pkg.Package_ID = cls.Package_ID)
    left join t_connector conn on (conn.Start_Object_ID = cls.Object_ID and conn.Connector_Type = 'Generalization')
    left join t_object scls on (conn.End_Object_ID = scls.Object_ID)
    where lower(cls.Stereotype) = 'featuretype'
    and cls.Object_Type = 'Class'
    and cls.Package_ID = $PKG_ID$
    order by pkg_name, super_name, name;
'''

PKG_QUERY = '''
    select pkg.package_id as package_id, pkg.Name as name, pkg.Notes as description
    from t_package pkg join t_object cls on (pkg.Package_ID = cls.Package_ID)
    where lower(cls.Stereotype) = 'featuretype'
    and cls.Object_Type = 'Class';
'''

ATTR_QUERY = '''
    select att.*
    from t_attribute att
    where att.Object_ID = $OBJ_ID$;
'''

ASSOC_QUERY = '''
    select cls.Object_ID as class_id, obj.Object_id as obj_id,
           obj.name as obj_name, obj.Note as obj_notes,
           COALESCE(obj.Alias, obj.Name) as obj_label,
           conn.destRole as obj_role,
           conn.SourceCard as card
    from t_object cls
    join t_connector conn on (conn.Start_Object_ID = cls.Object_ID and conn.Connector_Type = 'Association')
    join t_object obj on (conn.End_Object_ID = obj.Object_ID)
    where cls.Object_ID = $OBJ_ID$;
'''

CODELISTS_QUERY = '''
    select cls.Object_ID as object_id, coalesce(cls.Alias, cls.Name) as label,
           cls.Name as name, cls.Note as description
    from t_object cls
    where lower(cls.Stereotype) in ('codelist', 'type', 'datatype')
    and cls.Object_Type = 'Class'
    and cls.Package_ID = $PKG_ID$;
'''