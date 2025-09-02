***Settings***
Documentation    This is main test case file.
Library          test_suite.py

***Keywords***

App_Test_case_001
    [Documentation]     Verify Happy Path for PDD - CPU
    ${status}          TC_001_APP
    Should Not Be Equal As Integers    ${status}    1
    RETURN         Run Keyword And Return Status    ${status}

App_Test_case_002
    [Documentation]      Verify Happy Path for WELD - CPU
    ${status}          TC_002_APP
    Should Not Be Equal As Integers    ${status}    1
    RETURN         Run Keyword And Return Status    ${status}

App_Test_case_003
    [Documentation]      Verify Happy Path for PCB - CPU
    ${status}          TC_003_APP
    Should Not Be Equal As Integers    ${status}    1
    RETURN         Run Keyword And Return Status    ${status}

App_Test_case_004
    [Documentation]      Verify Happy Path for Worker Safety - CPU
    ${status}          TC_004_APP
    Should Not Be Equal As Integers    ${status}    1
    RETURN         Run Keyword And Return Status    ${status}




***Test Cases***

#ALL the test cases related to WELD usecase

APP_TC_001
    [Documentation]    Verify Happy Path for PDD - CPU
    [Tags]      app
    ${Status}    Run Keyword And Return Status   App_Test_case_001
    Should Not Be Equal As Integers    ${Status}    0

APP_TC_002
    [Documentation]    Verify Happy Path for WELD - CPU
    [Tags]      app
    ${Status}    Run Keyword And Return Status   App_Test_case_002
    Should Not Be Equal As Integers    ${Status}    0

APP_TC_003
    [Documentation]    Verify Happy Path for PCB - CPU
    [Tags]      app
    ${Status}    Run Keyword And Return Status   App_Test_case_003
    Should Not Be Equal As Integers    ${Status}    0

APP_TC_004
    [Documentation]    Verify Happy Path for Worker Safety - CPU
    [Tags]      app
    ${Status}    Run Keyword And Return Status   App_Test_case_004
    Should Not Be Equal As Integers    ${Status}    0

