async function fetchAllClasses_Student() {
    let response = await fetch('http://127.0.0.1:5000/mCS', { method: 'get', mode: 'cors' });

    if (response.ok) { // if HTTP-status is 200-299
        console.log(response);
        
    } else {
        alert("HTTP-Error: " + response.status);
    }

    console.log(response)
}


async function fetchCourseList(){
    let response = await fetch('http://127.0.0.1:5000/courseList', { method: 'get', mode: 'cors' });

    if (response.ok) { // if HTTP-status is 200-299
        console.log(response);
        
    } else {
        alert("HTTP-Error: " + response.status);
    }

    console.log(response)


}

async function fetchAllGrades() {

    //Await fetch response (make sure url matches local host and route we want to use in backend), define method 
    let response = await fetch('http://127.0.0.1:5000/grades', { method: 'GET'});


    //Error handling 
    if (response.ok) { // if HTTP-status is 200-299
        console.log(response);
        
    } else {
        alert("HTTP-Error: " + response.status);
    }

    //Send response data json to displayFunction to print it to the page 
    displayData(response);
}