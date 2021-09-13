# File list
## <strong> - register_service.sh </strong>
> This script will register your own service into Linux(ubuntu) service system.<br/>
> (!Caution) If you changed the service name "sample_service" to other thing then you must modify the $ServiceName of this file.
```bash
test@test-desktop:~/path/to/this/directory$ ./register_service.sh
Enter the password: <User`s password>
```

## <strong> - deregister_service.sh </strong>
> This script will remove that is already registered your service before into Linux(ubuntu) service system.<br/>
> (!Caution) If you changed the service name "sample_service" to other thing then you must modify the $ServiceName of this file.
```bash
test@test-desktop:~/path/to/this/directory$ ./deregister_service.sh
Enter the password: <User`s password>
```

## <strong> - sample_service </strong>
> This file includes service routines. you can modify it but not recommended.<br/>
> (!Caution) If you changed the service name "sample_service" to other thing then you must modify the $ServiceName of this file.

## <strong> - sample_service_main_script </strong>
> When the service "sample_service" is launched, this script file will be executed by the service.
